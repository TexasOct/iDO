"""
Configuration loader
Supports loading configuration from TOML and YAML files, with environment variable override support
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import toml
import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Configuration loader class"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_file()
        self._config: Dict[str, Any] = {}

    def _get_default_config_file(self) -> str:
        """Get default configuration file path

        Strategy:
        1. Always use ~/.config/ido/config.toml (standard user configuration directory)
        2. If file doesn't exist, will be automatically created from default template during load()
        3. No longer use project-internal configuration (avoid dev environment config mixing with production)
        """
        # User configuration directory (standard location, enforced)
        user_config_dir = Path.home() / ".config" / "ido"
        user_config_file = user_config_dir / "config.toml"

        logger.debug(f"Using user configuration directory: {user_config_file}")
        return str(user_config_file)

    def load(self) -> Dict[str, Any]:
        """Load configuration, create default configuration if it doesn't exist

        Configuration hierarchy (later overrides earlier):
        1. Project default config (backend/config/config.toml)
        2. User config (~/.config/ido/config.toml)
        """
        config_path = Path(self.config_file)

        # If configuration file doesn't exist, create default configuration
        if not config_path.exists():
            logger.debug(f"Configuration file doesn't exist: {self.config_file}")
            self._create_default_config(config_path)

        try:
            # Step 1: Load project default configuration
            project_config = self._load_project_config()

            # Step 2: Load user configuration file
            with open(self.config_file, "r", encoding="utf-8") as f:
                config_content = f.read()

            # Replace environment variables
            config_content = self._replace_env_vars(config_content)
            # Windows: Before TOML parsing, fix paths with backslashes in double quotes to avoid reserved escape sequence errors
            if os.name == "nt" and self.config_file.endswith(".toml"):
                config_content = self._sanitize_windows_paths(config_content)

            # Choose parser based on file extension
            if self.config_file.endswith(".toml"):
                user_config = toml.loads(config_content)
            else:
                # Default to YAML parser
                user_config = yaml.safe_load(config_content)

            # Step 3: Merge configurations (user config overrides project config)
            self._config = self._merge_configs(project_config, user_config)

            logger.debug(f"✓ Configuration file loaded successfully: {self.config_file}")
            logger.debug(f"✓ Merged with project defaults from: backend/config/config.toml")
            return self._config

        except (yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"Configuration file parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            raise

    def _load_project_config(self) -> Dict[str, Any]:
        """Load project default configuration from backend/config/config.toml

        Returns:
            Project configuration dictionary, or empty dict if file doesn't exist
        """
        # Get project config path (relative to this file)
        current_file = Path(__file__)
        project_config_file = current_file.parent / "config.toml"

        if not project_config_file.exists():
            logger.debug(f"Project config file not found: {project_config_file}")
            return {}

        try:
            with open(project_config_file, "r", encoding="utf-8") as f:
                config_content = f.read()

            # Replace environment variables
            config_content = self._replace_env_vars(config_content)

            # Parse TOML
            project_config = toml.loads(config_content)
            logger.debug(f"✓ Project config loaded: {project_config_file}")
            return project_config

        except Exception as e:
            logger.warning(f"Failed to load project config: {e}")
            return {}

    def _merge_configs(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries

        Args:
            base: Base configuration (project defaults)
            override: Override configuration (user config)

        Returns:
            Merged configuration dictionary

        Note:
            User config should NOT contain system-level settings like [processing].
            Only user-level settings (database path, screenshot path, etc.) should be in user config.
        """
        result = base.copy()

        # Filter out system-level sections from user config
        system_sections = {'processing', 'monitoring', 'image', 'image_optimization'}

        for key, value in override.items():
            # Skip system-level sections
            if key in system_sections:
                logger.debug(
                    f"Ignoring system-level section in user config: [{key}] "
                    "(use project config for system settings)"
                )
                continue

            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._merge_configs(result[key], value)
            else:
                # Override value
                result[key] = value

        return result

    def _create_default_config(self, config_path: Path) -> None:
        """Create default configuration file"""
        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Get default configuration content
            default_config = self._get_default_config_content()

            # Write configuration file
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(default_config)

            logger.debug(f"✓ Default configuration file created: {config_path}")

        except Exception as e:
            logger.error(f"Failed to create default configuration file: {e}")
            raise

    def _get_default_config_content(self) -> str:
        """Get default configuration content for user configuration

        Note: Only user-configurable items should be in user config.
        Development settings (logging, monitoring, etc.) are in project config.
        """
        # Avoid circular imports: use path directly, don't import get_data_dir
        config_dir = Path.home() / ".config" / "ido"
        data_dir = config_dir
        screenshots_dir = config_dir / "screenshots"

        return f"""# iDO User Configuration File
# Location: ~/.config/ido/config.toml
#
# This file contains user-level settings only.
# System-level settings ([processing], [monitoring], [image], etc.) are managed
# in project configuration (backend/config/config.toml) and cannot be overridden here.

[database]
# Database storage location
path = '{data_dir / "ido.db"}'

[screenshot]
# Screenshot storage location
save_path = '{screenshots_dir}'
# Force save interval when screenshots are being filtered as duplicates (seconds)
# Even if screenshots are identical, force save one after this interval
force_save_interval = 60
"""

    def _replace_env_vars(self, content: str) -> str:
        """Replace environment variable placeholders"""
        import re

        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ""
            return os.getenv(var_name, default_value)

        # Match ${VAR_NAME} or ${VAR_NAME:default_value} format
        pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"
        return re.sub(pattern, replace_var, content)

    def _sanitize_windows_paths(self, content: str) -> str:
        """Convert TOML double-quoted strings containing backslashes to single-quoted (only called on Windows).

        Example: key = "C:\\Users\\name" -> key = 'C:\\Users\\name'
        """
        import re

        # Match simple key-value lines like `key = "...\..."` where the value contains at least one backslash
        pattern = re.compile(
            r"^(\s*[A-Za-z0-9_.-]+\s*=\s*)\"([^\"]*\\\\[^\"]*)\"(\s*)$", re.MULTILINE
        )

        def repl(m):
            prefix, val, suffix = m.group(1), m.group(2), m.group(3)
            return f"{prefix}'{val}'{suffix}"

        return pattern.sub(repl, content)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value, supports dot-separated nested keys"""
        keys = key.split(".")
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> bool:
        """Set configuration value, supports dot-separated nested keys"""
        keys = key.split(".")
        config = self._config

        # Create nested structure
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the final key
        config[keys[-1]] = value
        return self.save()

    def save(self) -> bool:
        """Save configuration to file"""
        try:
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Save as TOML format
            with open(self.config_file, "w", encoding="utf-8") as f:
                toml.dump(self._config, f)

            logger.debug(f"✓ Configuration saved to: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for loading configuration"""
    loader = get_config(config_file)
    if loader._config:  # type: ignore[attr-defined]
        return loader._config  # type: ignore[attr-defined]
    return loader.load()


# Global configuration instance
_config_instance: Optional[ConfigLoader] = None


def get_config(config_file: Optional[str] = None) -> ConfigLoader:
    """Get global configuration instance"""
    global _config_instance
    if config_file is not None:
        _config_instance = ConfigLoader(config_file)
        _config_instance.load()
    elif _config_instance is None:
        _config_instance = ConfigLoader()
        _config_instance.load()
    return _config_instance
