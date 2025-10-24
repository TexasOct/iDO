"""
Settings 管理器
直接编辑 ~/.config/rewind/config.toml 中的配置
"""

from typing import Dict, Any, Optional
from pathlib import Path
from core.logger import get_logger
from core.paths import get_data_dir

logger = get_logger(__name__)


class SettingsManager:
    """配置管理器 - 直接编辑 config.toml"""

    def __init__(self, config_loader=None):
        """初始化 Settings 管理器

        Args:
            config_loader: ConfigLoader 实例，用于读写配置文件
        """
        self.config_loader = config_loader
        self._initialized = False

    def initialize(self, config_loader):
        """初始化配置加载器"""
        self.config_loader = config_loader
        self._initialized = True
        logger.info("✓ Settings 管理器已初始化")

    # ======================== LLM 配置 ========================

    def get_llm_settings(self) -> Dict[str, Any]:
        """获取 LLM 配置"""
        if not self.config_loader:
            return {}

        provider = self.config_loader.get('llm.default_provider', 'openai')
        config = self.config_loader.get(f'llm.{provider}', {})

        return {
            'provider': provider,
            'api_key': config.get('api_key', ''),
            'model': config.get('model', ''),
            'base_url': config.get('base_url', '')
        }

    def set_llm_settings(self, provider: str, api_key: str, model: str,
                         base_url: str) -> bool:
        """设置 LLM 配置"""
        if not self.config_loader:
            logger.error("配置加载器未初始化")
            return False

        try:
            # 更新默认提供商
            self.config_loader.set('llm.default_provider', provider)

            # 更新对应提供商的配置
            self.config_loader.set(f'llm.{provider}.api_key', api_key)
            self.config_loader.set(f'llm.{provider}.model', model)
            self.config_loader.set(f'llm.{provider}.base_url', base_url)

            logger.info(f"✓ LLM 配置已更新: {provider}")
            return True

        except Exception as e:
            logger.error(f"更新 LLM 配置失败: {e}")
            return False

    # ======================== 数据库配置 ========================

    def get_database_path(self) -> str:
        """获取数据库路径"""
        if not self.config_loader:
            return str(get_data_dir() / 'rewind.db')

        return self.config_loader.get('database.path',
                                      str(get_data_dir() / 'rewind.db'))

    def set_database_path(self, path: str) -> bool:
        """设置数据库路径（立即生效）

        当用户修改数据库路径时，会立即切换到新的数据库
        """
        if not self.config_loader:
            logger.error("配置加载器未初始化")
            return False

        try:
            # 保存到 config.toml
            self.config_loader.set('database.path', path)
            logger.info(f"✓ 数据库路径已更新: {path}")

            # 立即切换数据库（实时生效）
            from core.db import switch_database
            if switch_database(path):
                logger.info(f"✓ 已切换到新的数据库路径")
                return True
            else:
                logger.error(f"✗ 数据库路径已保存，但切换失败")
                return False

        except Exception as e:
            logger.error(f"更新数据库路径失败: {e}")
            return False

    # ======================== 截图配置 ========================

    def get_screenshot_path(self) -> str:
        """获取截图保存路径"""
        if not self.config_loader:
            return str(get_data_dir('screenshots'))

        return self.config_loader.get('screenshot.save_path',
                                      str(get_data_dir('screenshots')))

    def set_screenshot_path(self, path: str) -> bool:
        """设置截图保存路径"""
        if not self.config_loader:
            logger.error("配置加载器未初始化")
            return False

        try:
            self.config_loader.set('screenshot.save_path', path)
            logger.info(f"✓ 截图保存路径已更新: {path}")
            return True

        except Exception as e:
            logger.error(f"更新截图保存路径失败: {e}")
            return False

    # ======================== 通用配置操作 ========================

    def get(self, key: str, default: Any = None) -> Any:
        """获取任意配置项"""
        if not self.config_loader:
            return default

        return self.config_loader.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置任意配置项"""
        if not self.config_loader:
            logger.error("配置加载器未初始化")
            return False

        try:
            return self.config_loader.set(key, value)
        except Exception as e:
            logger.error(f"设置配置 {key} 失败: {e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        if not self.config_loader:
            return {}

        return self.config_loader._config.copy()

    def reload(self) -> bool:
        """重新加载配置文件"""
        if not self.config_loader:
            logger.error("配置加载器未初始化")
            return False

        try:
            self.config_loader.load()
            logger.info("✓ 配置文件已重新加载")
            return True

        except Exception as e:
            logger.error(f"重新加载配置文件失败: {e}")
            return False


# 全局 Settings 实例
_settings_instance: Optional[SettingsManager] = None


def get_settings() -> SettingsManager:
    """获取全局 Settings 实例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager()
    return _settings_instance


def init_settings(config_loader) -> SettingsManager:
    """初始化 Settings 管理器

    Args:
        config_loader: ConfigLoader 实例

    Returns:
        SettingsManager 实例
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager(config_loader)
    else:
        _settings_instance.initialize(config_loader)
    return _settings_instance
