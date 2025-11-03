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
        """获取默认配置文件路径

        策略：
        1. 总是使用 ~/.config/rewind/config.toml（标准用户配置目录）
        2. 如果文件不存在，会在 load() 时自动从默认模板创建
        3. 不再使用项目内的配置（避免开发环境配置混入生产）
        """
        # 用户配置目录（标准位置，强制使用）
        user_config_dir = Path.home() / ".config" / "rewind"
        user_config_file = user_config_dir / "config.toml"

        logger.info(f"使用用户配置目录: {user_config_file}")
        return str(user_config_file)

    def load(self) -> Dict[str, Any]:
        """加载配置，如果不存在则创建默认配置"""
        config_path = Path(self.config_file)

        # 如果配置文件不存在，创建默认配置
        if not config_path.exists():
            logger.info(f"配置文件不存在: {self.config_file}")
            self._create_default_config(config_path)

        try:
            # 加载配置文件
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_content = f.read()

            # 替换环境变量
            config_content = self._replace_env_vars(config_content)
            # Windows: 在 TOML 解析前，修正双引号中含反斜杠的路径，避免保留转义序列错误
            if os.name == 'nt' and self.config_file.endswith('.toml'):
                config_content = self._sanitize_windows_paths(config_content)

            # 根据文件扩展名选择解析器
            if self.config_file.endswith('.toml'):
                self._config = toml.loads(config_content)
            else:
                # 默认使用YAML解析器
                self._config = yaml.safe_load(config_content)

            logger.info(f"✓ 配置文件加载成功: {self.config_file}")
            return self._config

        except (yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"配置文件解析错误: {e}")
            raise
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise

    def _create_default_config(self, config_path: Path) -> None:
        """创建默认配置文件"""
        try:
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # 获取默认配置内容
            default_config = self._get_default_config_content()

            # 写入配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(default_config)

            logger.info(f"✓ 已创建默认配置文件: {config_path}")

        except Exception as e:
            logger.error(f"创建默认配置文件失败: {e}")
            raise

    def _get_default_config_content(self) -> str:
        """获取默认配置内容"""
        # 避免循环导入：直接使用路径，不导入 get_data_dir
        config_dir = Path.home() / ".config" / "rewind"
        data_dir = config_dir
        screenshots_dir = config_dir / "screenshots"

        return f"""# Rewind 应用配置文件
# 位置: ~/.config/rewind/config.toml

[server]
host = "0.0.0.0"
port = 8000
debug = false

[database]
# 数据库存储位置
path = '{data_dir / 'rewind.db'}'

[screenshot]
# 截图存储位置
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
        """替换环境变量占位符"""
        import re

        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ""
            return os.getenv(var_name, default_value)

        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default_value} 格式
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        return re.sub(pattern, replace_var, content)

    def _sanitize_windows_paths(self, content: str) -> str:
        """将包含反斜杠的 TOML 双引号字符串改为单引号包裹（仅 Windows 下调用）。

        示例：key = "C:\\Users\\name" -> key = 'C:\\Users\\name'
        """
        import re

        # 匹配形如 `key = "...\..."` 的简单键值行，值中至少包含一个反斜杠
        pattern = re.compile(r"^(\s*[A-Za-z0-9_.-]+\s*=\s*)\"([^\"]*\\\\[^\"]*)\"(\s*)$", re.MULTILINE)

        def repl(m):
            prefix, val, suffix = m.group(1), m.group(2), m.group(3)
            return f"{prefix}'{val}'{suffix}"

        return pattern.sub(repl, content)

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

    def set(self, key: str, value: Any) -> bool:
        """设置配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        config = self._config

        # 创建嵌套结构
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # 设置最后一个键
        config[keys[-1]] = value
        return self.save()

    def save(self) -> bool:
        """保存配置到文件"""
        try:
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存为 TOML 格式
            with open(self.config_file, 'w', encoding='utf-8') as f:
                toml.dump(self._config, f)

            logger.info(f"✓ 配置已保存到: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载配置的便捷函数"""
    loader = get_config(config_file)
    if loader._config:  # type: ignore[attr-defined]
        return loader._config  # type: ignore[attr-defined]
    return loader.load()


# 全局配置实例
_config_instance: Optional[ConfigLoader] = None


def get_config(config_file: Optional[str] = None) -> ConfigLoader:
    """获取全局配置实例"""
    global _config_instance
    if config_file is not None:
        _config_instance = ConfigLoader(config_file)
        _config_instance.load()
    elif _config_instance is None:
        _config_instance = ConfigLoader()
        _config_instance.load()
    return _config_instance
