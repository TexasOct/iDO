"""
统一日志系统
支持按配置输出到文件和控制台
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
from config.loader import get_config


class LoggerManager:
    """日志管理器"""
    
    def __init__(self):
        self._loggers: dict = {}
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """设置根日志器"""
        config = get_config()
        
        # 获取日志配置
        log_level = config.get('logging.level', 'INFO')
        logs_dir = config.get('logging.logs_dir', './logs')
        max_file_size = config.get('logging.max_file_size', '10MB')
        backup_count = config.get('logging.backup_count', 5)
        
        # 创建日志目录
        Path(logs_dir).mkdir(parents=True, exist_ok=True)
        
        # 设置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)
        
        # 文件处理器
        log_file = Path(logs_dir) / 'rewind_backend.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self._parse_size(max_file_size),
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)
        
        # 错误日志文件处理器
        error_log_file = Path(logs_dir) / 'error.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self._parse_size(max_file_size),
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        root_logger.addHandler(error_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """解析文件大小字符串"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]


# 全局日志管理器实例
_logger_manager = LoggerManager()


def get_logger(name: str) -> logging.Logger:
    """获取日志器的便捷函数"""
    return _logger_manager.get_logger(name)


def setup_logging():
    """设置日志系统（用于初始化）"""
    _logger_manager._setup_root_logger()
