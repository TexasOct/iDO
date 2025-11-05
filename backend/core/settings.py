"""
Settings manager
Directly edits configuration in ~/.config/rewind/config.toml
"""

from typing import Dict, Any, Optional
from core.logger import get_logger
from core.paths import get_data_dir

logger = get_logger(__name__)


class SettingsManager:
    """Configuration manager - directly edits config.toml"""

    def __init__(self, config_loader=None):
        """Initialize Settings manager

        Args:
            config_loader: ConfigLoader instance, used for reading and writing configuration files
        """
        self.config_loader = config_loader
        self._initialized = False

    def initialize(self, config_loader):
        """Initialize configuration loader"""
        self.config_loader = config_loader
        self._initialized = True
        logger.info("✓ Settings manager initialized")

    # ======================== LLM Configuration ========================

    def get_llm_settings(self) -> Dict[str, Any]:
        """Get LLM configuration"""
        if not self.config_loader:
            return {}

        provider = self.config_loader.get("llm.default_provider", "openai")
        config = self.config_loader.get(f"llm.{provider}", {})

        return {
            "provider": provider,
            "api_key": config.get("api_key", ""),
            "model": config.get("model", ""),
            "base_url": config.get("base_url", ""),
        }

    def set_llm_settings(
        self, provider: str, api_key: str, model: str, base_url: str
    ) -> bool:
        """Set LLM configuration"""
        if not self.config_loader:
            logger.error("Configuration loader not initialized")
            return False

        try:
            # Update default provider
            self.config_loader.set("llm.default_provider", provider)

            # Update corresponding provider configuration
            self.config_loader.set(f"llm.{provider}.api_key", api_key)
            self.config_loader.set(f"llm.{provider}.model", model)
            self.config_loader.set(f"llm.{provider}.base_url", base_url)

            logger.info(f"✓ LLM configuration updated: {provider}")
            return True

        except Exception as e:
            logger.error(f"Failed to update LLM configuration: {e}")
            return False

    # ======================== Database Configuration ========================

    def get_database_path(self) -> str:
        """Get database path"""
        if not self.config_loader:
            return str(get_data_dir() / "rewind.db")

        return self.config_loader.get(
            "database.path", str(get_data_dir() / "rewind.db")
        )

    def set_database_path(self, path: str) -> bool:
        """Set database path (takes effect immediately)

        When user modifies database path, it will immediately switch to new database
        """
        if not self.config_loader:
            logger.error("Configuration loader not initialized")
            return False

        try:
            # Save to config.toml
            self.config_loader.set("database.path", path)
            logger.info(f"✓ Database path updated: {path}")

            # Switch database immediately (real-time effect)
            from core.db import switch_database

            if switch_database(path):
                logger.info("✓ Switched to new database path")
                return True
            else:
                logger.error("✗ Database path saved but switch failed")
            return False

        except Exception as e:
            logger.error(f"Failed to switch database path: {e}")
            return False

    # ======================== Screenshot Configuration ========================

    def get_screenshot_path(self) -> str:
        """Get screenshot save path"""
        if not self.config_loader:
            return str(get_data_dir("screenshots"))

        return self.config_loader.get(
            "screenshot.save_path", str(get_data_dir("screenshots"))
        )

    def set_screenshot_path(self, path: str) -> bool:
        """Set screenshot save path"""
        if not self.config_loader:
            return False

        try:
            self.config_loader.set("screenshot.save_path", path)
            logger.info(f"✓ Screenshot save path updated: {path}")

            # Update image manager storage directory to maintain runtime consistency
            try:
                from processing.image_manager import get_image_manager

                image_manager = get_image_manager()
                image_manager.update_storage_path(path)
                logger.info(f"✓ Image manager storage path updated: {path}")

                return True

            except Exception as e:
                logger.error(f"Failed to set screenshot save path: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to update screenshot save path in config: {e}")
            return False

    # ======================== Live2D Configuration ========================

    @staticmethod
    def _default_live2d_settings() -> Dict[str, Any]:
        default_model = "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/shizuku/shizuku.model.json"
        return {
            "enabled": False,
            "selected_model_url": default_model,
            "model_dir": "",
            "remote_models": [default_model],
        }

    def get_live2d_settings(self) -> Dict[str, Any]:
        """Get Live2D related configuration"""
        defaults = self._default_live2d_settings()
        if not self.config_loader:
            return defaults

        try:
            raw_value = self.config_loader.get("live2d", {}) or {}
            if not isinstance(raw_value, dict):
                raw_value = {}
            merged = {**defaults, **raw_value}

            remote_models = merged.get("remote_models") or []
            if not isinstance(remote_models, list):
                remote_models = []

            # Normalize remote models: strip whitespace, remove duplicates and empty values
            normalized_remotes = []
            seen = set()
            for item in remote_models:
                url = str(item).strip()
                if url and url not in seen:
                    normalized_remotes.append(url)
                    seen.add(url)
            merged["remote_models"] = normalized_remotes

            merged["enabled"] = bool(merged.get("enabled", False))
            merged["selected_model_url"] = str(
                merged.get("selected_model_url", "") or ""
            )
            merged["model_dir"] = str(merged.get("model_dir", "") or "")

            return merged
        except Exception as exc:
            logger.warning(f"Failed to read Live2D settings, using defaults: {exc}")
            return defaults

    def update_live2d_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update Live2D configuration values"""
        if not self.config_loader:
            logger.error("Configuration loader not initialized")
            return self._default_live2d_settings()

        current = self.get_live2d_settings()
        merged = current.copy()

        if "enabled" in updates:
            merged["enabled"] = bool(updates.get("enabled", False))
        if "selected_model_url" in updates:
            merged["selected_model_url"] = str(
                updates.get("selected_model_url") or ""
            ).strip()
        if "model_dir" in updates:
            merged["model_dir"] = str(updates.get("model_dir") or "").strip()
        if "remote_models" in updates and updates["remote_models"] is not None:
            remote_models = updates.get("remote_models") or []
            if not isinstance(remote_models, list):
                remote_models = []
            sanitized = []
            seen = set()
            for item in remote_models:
                url = str(item).strip()
                if url and url not in seen:
                    sanitized.append(url)
                    seen.add(url)
            merged["remote_models"] = sanitized

        try:
            self.config_loader.set("live2d", merged)
            logger.info("✓ Live2D settings updated")
        except Exception as exc:
            logger.error(f"Failed to update Live2D settings: {exc}")

        return merged

    # ======================== Image Optimization Configuration ========================

    def get_image_optimization_config(self) -> Dict[str, Any]:
        """Get image optimization configuration"""
        if not self.config_loader:
            return self._get_default_image_optimization_config()

        try:
            enabled = self.config_loader.get("image_optimization.enabled", True)
            strategy = self.config_loader.get("image_optimization.strategy", "hybrid")
            phash_threshold = float(
                self.config_loader.get("image_optimization.phash_threshold", 0.15)
            )
            min_interval = float(
                self.config_loader.get("image_optimization.min_sampling_interval", 2.0)
            )
            max_images = int(
                self.config_loader.get("image_optimization.max_images_per_event", 8)
            )
            enable_content = self.config_loader.get(
                "image_optimization.enable_content_analysis", True
            )
            enable_text = self.config_loader.get(
                "image_optimization.enable_text_detection", False
            )

            return {
                "enabled": enabled,
                "strategy": strategy,
                "phash_threshold": phash_threshold,
                "min_interval": min_interval,
                "max_images": max_images,
                "enable_content_analysis": enable_content,
                "enable_text_detection": enable_text,
            }
        except Exception as e:
            logger.warning(
                f"Failed to read image optimization configuration: {e}, using default configuration"
            )
            return self._get_default_image_optimization_config()

    def set_image_optimization_config(self, config: Dict[str, Any]) -> bool:
        """Set image optimization configuration"""
        if not self.config_loader:
            return False

        try:
            self.config_loader.set(
                "image_optimization.enabled", config.get("enabled", True)
            )
            self.config_loader.set(
                "image_optimization.strategy", config.get("strategy", "hybrid")
            )
            self.config_loader.set(
                "image_optimization.phash_threshold",
                config.get("phash_threshold", 0.15),
            )
            self.config_loader.set(
                "image_optimization.min_sampling_interval",
                config.get("min_interval", 2.0),
            )
            self.config_loader.set(
                "image_optimization.max_images_per_event", config.get("max_images", 8)
            )
            self.config_loader.set(
                "image_optimization.enable_content_analysis",
                config.get("enable_content_analysis", True),
            )
            self.config_loader.set(
                "image_optimization.enable_text_detection",
                config.get("enable_text_detection", False),
            )
            logger.info(f"Image optimization configuration updated: {config}")
            return True
        except Exception as e:
            logger.error(f"Failed to set image optimization configuration: {e}")
            return False

    def _get_default_image_optimization_config() -> Dict[str, Any]:
        """Get default image optimization configuration"""
        return {
            "enabled": True,
            "strategy": "hybrid",
            "phash_threshold": 0.15,
            "min_interval": 2.0,
            "max_images": 8,
            "enable_content_analysis": True,
            "enable_text_detection": False,
        }

    # ======================== Friendly Chat Configuration ========================

    @staticmethod
    def _default_friendly_chat_settings() -> Dict[str, Any]:
        """Get default friendly chat configuration"""
        return {
            "enabled": False,
            "interval": 20,  # minutes
            "data_window": 20,  # minutes
            "enable_system_notification": True,
            "enable_live2d_display": True,
        }

    def get_friendly_chat_settings(self) -> Dict[str, Any]:
        """Get friendly chat configuration"""
        defaults = self._default_friendly_chat_settings()
        if not self.config_loader:
            return defaults

        try:
            raw_value = self.config_loader.get("friendly_chat", {}) or {}
            if not isinstance(raw_value, dict):
                raw_value = {}
            merged = {**defaults, **raw_value}

            # Validate and normalize values
            merged["enabled"] = bool(merged.get("enabled", False))
            merged["interval"] = max(5, min(120, int(merged.get("interval", 20))))
            merged["data_window"] = max(5, min(120, int(merged.get("data_window", 20))))
            merged["enable_system_notification"] = bool(
                merged.get("enable_system_notification", True)
            )
            merged["enable_live2d_display"] = bool(
                merged.get("enable_live2d_display", True)
            )

            return merged
        except Exception as exc:
            logger.warning(
                f"Failed to read friendly chat settings, using defaults: {exc}"
            )
            return defaults

    def update_friendly_chat_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update friendly chat configuration values"""
        if not self.config_loader:
            logger.error("Configuration loader not initialized")
            return self._default_friendly_chat_settings()

        current = self.get_friendly_chat_settings()
        merged = current.copy()

        if "enabled" in updates:
            merged["enabled"] = bool(updates.get("enabled", False))
        if "interval" in updates:
            merged["interval"] = max(5, min(120, int(updates.get("interval", 20))))
        if "data_window" in updates:
            merged["data_window"] = max(
                5, min(120, int(updates.get("data_window", 20)))
            )
        if "enable_system_notification" in updates:
            merged["enable_system_notification"] = bool(
                updates.get("enable_system_notification", True)
            )
        if "enable_live2d_display" in updates:
            merged["enable_live2d_display"] = bool(
                updates.get("enable_live2d_display", True)
            )

        try:
            self.config_loader.set("friendly_chat", merged)
            logger.info("✓ Friendly chat settings updated")
        except Exception as exc:
            logger.error(f"Failed to update friendly chat settings: {exc}")

        return merged

    # ======================== Image Compression Configuration ========================

    def get_image_compression_config(self) -> Dict[str, Any]:
        """Get image compression configuration"""
        if not self.config_loader:
            return self._get_default_image_compression_config()

        try:
            compression_level = self.config_loader.get(
                "image_optimization.compression_level", "aggressive"
            )
            enable_cropping = self.config_loader.get(
                "image_optimization.enable_region_cropping", False
            )
            crop_threshold = int(
                self.config_loader.get("image_optimization.crop_threshold", 30)
            )

            return {
                "compression_level": compression_level,
                "enable_region_cropping": enable_cropping,
                "crop_threshold": crop_threshold,
            }
        except Exception as e:
            logger.warning(
                f"Failed to read image compression configuration: {e}, using default configuration"
            )
            return self._get_default_image_compression_config()

    def set_image_compression_config(self, config: Dict[str, Any]) -> bool:
        """Set image compression configuration

        Args:
            config: Configuration dictionary, containing:
                - compression_level: Compression level (ultra/aggressive/balanced/quality)
                - enable_region_cropping: Whether to enable region cropping
                - crop_threshold: Cropping threshold percentage
        """
        if not self.config_loader:
            logger.error("Configuration loader not initialized")
            return False

        try:
            # Validate compression level
            valid_levels = ["ultra", "aggressive", "balanced", "quality"]
            compression_level = config.get("compression_level", "aggressive")
            if compression_level not in valid_levels:
                logger.warning(
                    f"Invalid compression level {compression_level}, using default value 'aggressive'"
                )
                compression_level = "aggressive"

            # Update configuration
            self.config_loader.set(
                "image_optimization.compression_level", compression_level
            )
            self.config_loader.set(
                "image_optimization.enable_region_cropping",
                config.get("enable_region_cropping", False),
            )
            self.config_loader.set(
                "image_optimization.crop_threshold", config.get("crop_threshold", 30)
            )

            logger.info(
                f"✓ Image compression configuration updated: level={compression_level}, cropping={config.get('enable_region_cropping', False)}"
            )

            # Reinitialize image optimizer to apply new configuration
            try:
                from processing.image_compression import get_image_optimizer

                optimizer = get_image_optimizer()
                optimizer.reinitialize(
                    compression_level=compression_level,
                    enable_cropping=config.get("enable_region_cropping", False),
                    crop_threshold=config.get("crop_threshold", 30),
                )
                logger.info("✓ Image optimizer reinitialized")
            except Exception as e:
                logger.warning(f"Failed to reinitialize image optimizer: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to update image compression configuration: {e}")
            return False

    @staticmethod
    def _get_default_image_compression_config() -> Dict[str, Any]:
        """Get default image compression configuration"""
        return {
            "compression_level": "aggressive",
            "enable_region_cropping": False,
            "crop_threshold": 30,
        }

    # ======================== General Configuration Operations ========================

    def get(self, key: str, default: Any = None) -> Any:
        """Get any configuration item"""
        if not self.config_loader:
            return default

        return self.config_loader.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set any configuration item"""
        if not self.config_loader:
            logger.error("Configuration loader not initialized")
            return False

        try:
            return self.config_loader.set(key, value)
        except Exception as e:
            logger.error(f"Failed to set configuration {key}: {e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration"""
        if not self.config_loader:
            return {}

        return self.config_loader._config.copy()

    def reload(self) -> bool:
        """Reload configuration file"""
        if not self.config_loader:
            logger.error("Configuration loader not initialized")
            return False

        try:
            self.config_loader.load()
            logger.info("✓ Configuration file reloaded")
            return True

        except Exception as e:
            logger.error(f"Failed to reload configuration file: {e}")
            return False


# Global Settings instance
_settings_instance: Optional[SettingsManager] = None


def get_settings() -> SettingsManager:
    """Get global Settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager()
    return _settings_instance


def init_settings(config_loader) -> SettingsManager:
    """Initialize Settings manager

    Args:
        config_loader: ConfigLoader instance

    Returns:
        SettingsManager instance
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager(config_loader)
    else:
        _settings_instance.initialize(config_loader)
    return _settings_instance
