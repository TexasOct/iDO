"""
Unified logging system
Supports output to files and console based on configuration
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

import toml


def _get_project_config_path() -> Path:
    """Get project configuration file path (not user config)

    Logger should always use project-internal configuration for development settings,
    not user configuration which is for data paths and user preferences.
    """
    # Get the backend directory
    backend_dir = Path(__file__).parent.parent
    config_file = backend_dir / "config" / "config.toml"

    if not config_file.exists():
        raise FileNotFoundError(f"Project config file not found: {config_file}")

    return config_file


def _load_project_config() -> dict:
    """Load project configuration directly from project config file"""
    config_path = _get_project_config_path()

    with open(config_path, "r", encoding="utf-8") as f:
        return toml.load(f)


# Initialize root logger at module import time to ensure all loggers inherit correct level
def _init_root_logger_early():
    """Initialize root logger early to prevent any DEBUG logs before proper setup"""
    try:
        project_config = _load_project_config()
        logging_config = project_config.get("logging", {})
        log_level = logging_config.get("level", "INFO")

        # Set root logger level immediately
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
    except Exception:
        # If project config loading fails, use INFO as default
        logging.getLogger().setLevel(logging.INFO)


# Initialize root logger level as soon as this module is imported
_init_root_logger_early()


class LoggerManager:
    """Log manager"""

    def __init__(self):
        self._loggers: dict = {}
        self._setup_root_logger()

    def _setup_root_logger(self):
        """Setup root logger using project configuration (not user configuration)"""
        # Use project config directly for logging settings
        # This ensures development settings are not overridden by user config
        project_config = _load_project_config()

        # Get logging configuration from project config
        logging_config = project_config.get("logging", {})
        log_level = logging_config.get("level", "INFO")
        logs_dir = logging_config.get("logs_dir", "./logs")
        max_file_size = logging_config.get("max_file_size", "10MB")
        backup_count = logging_config.get("backup_count", 5)

        # Create log directory
        Path(logs_dir).mkdir(parents=True, exist_ok=True)

        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)

        # File handler
        log_file = Path(logs_dir) / "ido_backend.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self._parse_size(max_file_size),
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

        # Error log file handler
        error_log_file = Path(logs_dir) / "error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self._parse_size(max_file_size),
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        root_logger.addHandler(error_handler)

    def _parse_size(self, size_str: str) -> int:
        """Parse file size string"""
        size_str = size_str.upper()
        if size_str.endswith("KB"):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith("MB"):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith("GB"):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

    def get_logger(self, name: str) -> logging.Logger:
        """Get logger with specified name"""
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]


# Global log manager instance (lazy initialization to avoid circular imports)
_logger_manager: Optional[LoggerManager] = None


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get logger"""
    global _logger_manager

    # Lazy initialization: create instance on first call
    if _logger_manager is None:
        _logger_manager = LoggerManager()

    return _logger_manager.get_logger(name)


def setup_logging():
    """Setup logging system (for initialization or reloading)

    Note: This function uses project configuration, not user configuration.
    """
    global _logger_manager

    if _logger_manager is None:
        _logger_manager = LoggerManager()
    else:
        _logger_manager._setup_root_logger()
