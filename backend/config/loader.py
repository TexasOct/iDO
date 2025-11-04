"""
Configuration loader
Supports loading configuration from TOML and YAML files, with environment variable override support
"""

import os
import yaml
import toml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Configuration loader class"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_file()
        self._config: Dict[str, Any] = {}

    def _get_default_config_file(self) -> str:
        """Get default configuration file path

        Strategy:
        1. Always use ~/.config/rewind/config.toml (standard user configuration directory)
        2. If file doesn't exist, will be automatically created from default template during load()
        3. No longer use project-internal configuration (avoid dev environment config mixing with production)
        """
        # User configuration directory (standard location, enforced)
        user_config_dir = Path.home() / ".config" / "rewind"
        user_config_file = user_config_dir / "config.toml"

        logger.info(f"Using user configuration directory: {user_config_file}")
        return str(user_config_file)

    def load(self) -> Dict[str, Any]:
        """Load configuration, create default configuration if it doesn't exist"""
        config_path = Path(self.config_file)

        # If configuration file doesn't exist, create default configuration
        if not config_path.exists():
            logger.info(f"Configuration file doesn't exist: {self.config_file}")
            self._create_default_config(config_path)

        try:
            # Load configuration file
            with open(self.config_file, "r", encoding="utf-8") as f:
                config_content = f.read()

            # Replace environment variables
            config_content = self._replace_env_vars(config_content)
            # Windows: Before TOML parsing, fix paths with backslashes in double quotes to avoid reserved escape sequence errors
            if os.name == "nt" and self.config_file.endswith(".toml"):
                config_content = self._sanitize_windows_paths(config_content)

            # Choose parser based on file extension
            if self.config_file.endswith(".toml"):
                self._config = toml.loads(config_content)
            else:
                # Default to YAML parser
                self._config = yaml.safe_load(config_content)

            logger.info(f"✓ Configuration file loaded successfully: {self.config_file}")
            return self._config

        except (yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"Configuration file parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            raise

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

            logger.info(f"✓ Default configuration file created: {config_path}")

        except Exception as e:
            logger.error(f"Failed to create default configuration file: {e}")
            raise

    def _get_default_config_content(self) -> str:
        """Get default configuration content"""
        # Avoid circular imports: use path directly, don't import get_data_dir
        config_dir = Path.home() / ".config" / "rewind"
        data_dir = config_dir
        screenshots_dir = config_dir / "screenshots"

        return f"""# Rewind application configuration file
# Location: ~/.config/rewind/config.toml

[server]
host = "0.0.0.0"
port = 8000
debug = false

[database]
# Database storage location
path = '{data_dir / "rewind.db"}'

[screenshot]
# Screenshot storage location
save_path = '{screenshots_dir}'

[llm]
default_provider = "openai"

[llm.openai]
api_key = "your_api_key_here"
model = "gpt-4"
base_url = "https://api.openai.com/v1"

[llm.qwen3vl]
api_key = "your_api_key_here"
model = "qwen-vl-max"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

[monitoring]
window_size = 20
capture_interval = 0.2
processing_interval = 10
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

            logger.info(f"✓ Configuration saved to: {self.config_file}")
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
