"""
Settings 管理器
提供应用级别的持久化配置管理
支持从配置文件和数据库读取配置，优先级：数据库 > 配置文件 > 硬编码默认值
"""

from typing import Dict, Any, Optional
from pathlib import Path
from core.logger import get_logger
from core.paths import get_data_dir

logger = get_logger(__name__)


class SettingsManager:
    """配置管理器"""

    # 默认配置值
    DEFAULT_SETTINGS = {
        'llm.provider': ('openai', 'string'),  # (value, type)
        'llm.api_key': ('', 'string'),
        'llm.model': ('gpt-4', 'string'),
        'llm.base_url': ('https://api.openai.com/v1', 'string'),
        'database.path': (str(get_data_dir() / 'rewind.db'), 'string'),
        'screenshot.save_path': (str(get_data_dir('screenshots')), 'string'),
    }

    def __init__(self, db_manager=None):
        """初始化 Settings 管理器"""
        self.db = db_manager
        self._cache: Dict[str, Any] = {}
        self._initialized = False

    def initialize(self, db_manager):
        """初始化数据库管理器"""
        self.db = db_manager
        self._init_default_settings()
        self._initialized = True

    def _init_default_settings(self):
        """初始化数据库中的默认配置"""
        if not self.db:
            logger.warning("数据库管理器未初始化")
            return

        try:
            # 检查是否已初始化
            existing = self.db.get_all_settings()
            if existing:
                logger.info(f"数据库中已有 {len(existing)} 个配置项")
                return

            # 从配置文件读取值并写入数据库
            from config.loader import get_config
            config = get_config()

            # 初始化 LLM 配置
            default_provider = config.get('llm.default_provider', 'openai')
            llm_config = config.get(f'llm.{default_provider}', {})

            self.db.set_setting(
                'llm.provider',
                default_provider,
                'string',
                'LLM 供应商'
            )
            self.db.set_setting(
                'llm.api_key',
                llm_config.get('api_key', ''),
                'string',
                'LLM API 密钥'
            )
            self.db.set_setting(
                'llm.model',
                llm_config.get('model', 'gpt-4'),
                'string',
                'LLM 模型名称'
            )
            self.db.set_setting(
                'llm.base_url',
                llm_config.get('base_url', 'https://api.openai.com/v1'),
                'string',
                'LLM API 基础 URL'
            )

            # 初始化数据库路径
            db_url = config.get('database.url', 'sqlite:///./rewind.db')
            if db_url.startswith('sqlite:///'):
                db_path = db_url[10:]
            else:
                db_path = str(get_data_dir() / 'rewind.db')

            self.db.set_setting(
                'database.path',
                db_path,
                'string',
                '数据库文件路径'
            )

            # 初始化截屏保存路径
            screenshot_path = str(get_data_dir('screenshots'))
            self.db.set_setting(
                'screenshot.save_path',
                screenshot_path,
                'string',
                '截屏保存目录'
            )

            logger.info("数据库默认配置初始化完成")
        except Exception as e:
            logger.warning(f"初始化默认配置失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if not self.db:
            # 如果数据库未初始化，使用硬编码默认值
            if key in self.DEFAULT_SETTINGS:
                return self.DEFAULT_SETTINGS[key][0]
            return default

        # 先尝试从缓存读取
        if key in self._cache:
            return self._cache[key]

        # 从数据库读取
        value = self.db.get_setting(key)
        if value is not None:
            self._cache[key] = value
            return value

        # 使用硬编码默认值
        if key in self.DEFAULT_SETTINGS:
            default_value = self.DEFAULT_SETTINGS[key][0]
            self._cache[key] = default_value
            return default_value

        return default

    def set(self, key: str, value: Any, setting_type: str = 'string') -> bool:
        """设置配置值"""
        if not self.db:
            logger.warning("数据库管理器未初始化，无法保存配置")
            return False

        try:
            # 转换值为字符串
            str_value = str(value)
            self.db.set_setting(key, str_value, setting_type)
            # 更新缓存
            self._cache[key] = value
            logger.info(f"配置已保存: {key} = {str_value}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        if not self.db:
            return {}
        return self.db.get_all_settings()

    def get_llm_settings(self) -> Dict[str, str]:
        """获取 LLM 配置"""
        return {
            'provider': self.get('llm.provider', 'openai'),
            'api_key': self.get('llm.api_key', ''),
            'model': self.get('llm.model', 'gpt-4'),
            'base_url': self.get('llm.base_url', 'https://api.openai.com/v1'),
        }

    def set_llm_settings(self, provider: str, api_key: str, model: str, base_url: str) -> bool:
        """设置 LLM 配置"""
        all_success = True
        all_success &= self.set('llm.provider', provider, 'string')
        all_success &= self.set('llm.api_key', api_key, 'string')
        all_success &= self.set('llm.model', model, 'string')
        all_success &= self.set('llm.base_url', base_url, 'string')
        return all_success

    def get_database_path(self) -> str:
        """获取数据库路径"""
        return self.get('database.path', str(get_data_dir() / 'rewind.db'))

    def get_screenshot_path(self) -> str:
        """获取截屏保存路径"""
        return self.get('screenshot.save_path', str(get_data_dir('screenshots')))

    def set_database_path(self, path: str) -> bool:
        """设置数据库路径"""
        return self.set('database.path', path, 'string')

    def set_screenshot_path(self, path: str) -> bool:
        """设置截屏保存路径"""
        return self.set('screenshot.save_path', path, 'string')


# 全局 Settings 实例
_settings_instance: Optional[SettingsManager] = None


def get_settings() -> SettingsManager:
    """获取全局 Settings 实例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager()
    return _settings_instance


def init_settings(db_manager) -> SettingsManager:
    """初始化 Settings 管理器"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager(db_manager)
    else:
        _settings_instance.initialize(db_manager)
    return _settings_instance
