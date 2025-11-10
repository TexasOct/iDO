"""
Unified logging system
Supports output to files and console based on configuration
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
from config.loader import get_config


class LoggerManager:
    """Log manager"""

    def __init__(self):
        self._loggers: dict = {}
        self._setup_root_logger()

    def _setup_root_logger(self):
        """Setup root logger"""
        config = get_config()

        # Get logging configuration
        log_level = config.get("logging.level", "INFO")
        logs_dir = config.get("logging.logs_dir", "./logs")
        max_file_size = config.get("logging.max_file_size", "10MB")
        backup_count = config.get("logging.backup_count", 5)

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
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
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
    """Setup logging system (for initialization)"""
    global _logger_manager

    if _logger_manager is None:
        _logger_manager = LoggerManager()
    else:
        _logger_manager._setup_root_logger()
