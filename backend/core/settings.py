"""
Settings 管理器
直接编辑 ~/.config/rewind/config.toml 中的配置
"""

from typing import Dict, Any, Optional
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
                logger.info("✓ 已切换到新的数据库路径")
                return True
            else:
                logger.error("✗ 数据库路径已保存，但切换失败")
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

            # 更新图片管理器的存储目录，保持运行时一致
            try:
                from processing.image_manager import get_image_manager

                image_manager = get_image_manager()
                image_manager.update_storage_path(path)
            except Exception as exc:
                logger.error(f"同步更新截图存储目录失败: {exc}")

            return True

        except Exception as e:
            logger.error(f"更新截图保存路径失败: {e}")
            return False

    # ======================== 图像优化配置 ========================

    def get_image_optimization_config(self) -> Dict[str, Any]:
        """获取图像优化配置"""
        if not self.config_loader:
            return self._get_default_image_optimization_config()

        try:
            enabled = self.config_loader.get('image_optimization.enabled', True)
            strategy = self.config_loader.get('image_optimization.strategy', 'hybrid')
            phash_threshold = float(self.config_loader.get('image_optimization.phash_threshold', 0.15))
            min_interval = float(self.config_loader.get('image_optimization.min_sampling_interval', 2.0))
            max_images = int(self.config_loader.get('image_optimization.max_images_per_event', 8))
            enable_content = self.config_loader.get('image_optimization.enable_content_analysis', True)
            enable_text = self.config_loader.get('image_optimization.enable_text_detection', False)

            return {
                'enabled': enabled,
                'strategy': strategy,
                'phash_threshold': phash_threshold,
                'min_interval': min_interval,
                'max_images': max_images,
                'enable_content_analysis': enable_content,
                'enable_text_detection': enable_text
            }
        except Exception as e:
            logger.warning(f"读取图像优化配置失败: {e}，使用默认配置")
            return self._get_default_image_optimization_config()

    def set_image_optimization_config(self, config: Dict[str, Any]) -> bool:
        """设置图像优化配置"""
        if not self.config_loader:
            logger.error("配置加载器未初始化")
            return False

        try:
            self.config_loader.set('image_optimization.enabled', config.get('enabled', True))
            self.config_loader.set('image_optimization.strategy', config.get('strategy', 'hybrid'))
            self.config_loader.set('image_optimization.phash_threshold', config.get('phash_threshold', 0.15))
            self.config_loader.set('image_optimization.min_sampling_interval', config.get('min_interval', 2.0))
            self.config_loader.set('image_optimization.max_images_per_event', config.get('max_images', 8))
            self.config_loader.set('image_optimization.enable_content_analysis', config.get('enable_content_analysis', True))
            self.config_loader.set('image_optimization.enable_text_detection', config.get('enable_text_detection', False))

            logger.info(f"✓ 图像优化配置已更新: {config}")
            return True
        except Exception as e:
            logger.error(f"更新图像优化配置失败: {e}")
            return False

    @staticmethod
    def _get_default_image_optimization_config() -> Dict[str, Any]:
        """获取默认的图像优化配置"""
        return {
            'enabled': True,
            'strategy': 'hybrid',
            'phash_threshold': 0.15,
            'min_interval': 2.0,
            'max_images': 8,
            'enable_content_analysis': True,
            'enable_text_detection': False
        }

    # ======================== 图像压缩配置 ========================

    def get_image_compression_config(self) -> Dict[str, Any]:
        """获取图像压缩配置"""
        if not self.config_loader:
            return self._get_default_image_compression_config()

        try:
            compression_level = self.config_loader.get('image_optimization.compression_level', 'aggressive')
            enable_cropping = self.config_loader.get('image_optimization.enable_region_cropping', False)
            crop_threshold = int(self.config_loader.get('image_optimization.crop_threshold', 30))

            return {
                'compression_level': compression_level,
                'enable_region_cropping': enable_cropping,
                'crop_threshold': crop_threshold
            }
        except Exception as e:
            logger.warning(f"读取图像压缩配置失败: {e}，使用默认配置")
            return self._get_default_image_compression_config()

    def set_image_compression_config(self, config: Dict[str, Any]) -> bool:
        """设置图像压缩配置

        Args:
            config: 配置字典，包含：
                - compression_level: 压缩级别 (ultra/aggressive/balanced/quality)
                - enable_region_cropping: 是否启用区域裁剪
                - crop_threshold: 裁剪阈值百分比
        """
        if not self.config_loader:
            logger.error("配置加载器未初始化")
            return False

        try:
            # 验证压缩级别
            valid_levels = ['ultra', 'aggressive', 'balanced', 'quality']
            compression_level = config.get('compression_level', 'aggressive')
            if compression_level not in valid_levels:
                logger.warning(f"无效的压缩级别 {compression_level}，使用默认值 'aggressive'")
                compression_level = 'aggressive'

            # 更新配置
            self.config_loader.set('image_optimization.compression_level', compression_level)
            self.config_loader.set('image_optimization.enable_region_cropping', config.get('enable_region_cropping', False))
            self.config_loader.set('image_optimization.crop_threshold', config.get('crop_threshold', 30))

            logger.info(f"✓ 图像压缩配置已更新: level={compression_level}, cropping={config.get('enable_region_cropping', False)}")

            # 重新初始化图像优化器以应用新配置
            try:
                from processing.image_compression import get_image_optimizer
                optimizer = get_image_optimizer()
                optimizer.reinitialize(
                    compression_level=compression_level,
                    enable_cropping=config.get('enable_region_cropping', False),
                    crop_threshold=config.get('crop_threshold', 30)
                )
                logger.info("✓ 图像优化器已重新初始化")
            except Exception as e:
                logger.warning(f"重新初始化图像优化器失败: {e}")

            return True

        except Exception as e:
            logger.error(f"更新图像压缩配置失败: {e}")
            return False

    @staticmethod
    def _get_default_image_compression_config() -> Dict[str, Any]:
        """获取默认的图像压缩配置"""
        return {
            'compression_level': 'aggressive',
            'enable_region_cropping': False,
            'crop_threshold': 30
        }

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
