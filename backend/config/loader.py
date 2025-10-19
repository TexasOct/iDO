"""
配置加载器
支持从 TOML 和 YAML 文件加载配置，并支持环境变量覆盖
"""

import os
import yaml
import toml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器类"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_file()
        self._config: Dict[str, Any] = {}
    
    def _get_default_config_file(self) -> str:
        """获取默认配置文件路径，优先使用TOML格式"""
        current_dir = Path(__file__).parent
        toml_file = current_dir / "config.toml"
        yaml_file = current_dir / "config.yaml"
        
        if toml_file.exists():
            return str(toml_file)
        elif yaml_file.exists():
            return str(yaml_file)
        else:
            return str(toml_file)  # 默认返回TOML文件路径
    
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            # 加载配置文件
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # 替换环境变量
            config_content = self._replace_env_vars(config_content)
            
            # 根据文件扩展名选择解析器
            if self.config_file.endswith('.toml'):
                self._config = toml.loads(config_content)
            else:
                # 默认使用YAML解析器
                self._config = yaml.safe_load(config_content)
            
            logger.info(f"配置文件加载成功: {self.config_file}")
            return self._config
            
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {self.config_file}")
            raise
        except (yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"配置文件解析错误: {e}")
            raise
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise
    
    def _replace_env_vars(self, content: str) -> str:
        """替换环境变量占位符"""
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ""
            return os.getenv(var_name, default_value)
        
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default_value} 格式
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        return re.sub(pattern, replace_var, content)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载配置的便捷函数"""
    loader = ConfigLoader(config_file)
    return loader.load()


# 全局配置实例
_config_instance: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
        _config_instance.load()
    return _config_instance
