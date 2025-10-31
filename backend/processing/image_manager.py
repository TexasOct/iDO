"""
图片管理器
负责截图的内存缓存、缩略图生成、压缩和持久化策略
"""

import base64
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
import io
from collections import OrderedDict
from core.logger import get_logger
from core.paths import get_data_dir, ensure_dir

logger = get_logger(__name__)


class ImageManager:
    """图片管理器 - 管理截图的内存缓存和持久化"""

    def __init__(
        self,
        memory_cache_size: int = 500,  # 内存中最多保留的图片数量（默认提高到 500，可通过配置覆盖）
        thumbnail_size: Tuple[int, int] = (400, 225),  # 缩略图尺寸 (16:9)
        thumbnail_quality: int = 75,  # 缩略图质量
        max_age_hours: int = 24,  # 临时文件最大保留时间
        base_dir: Optional[str] = None,  # 截图存储根目录（覆盖配置）
    ):
        # 尝试从全局配置中读取覆盖值：配置键为 image.memory_cache_size
        try:
            from core.settings import get_settings
            configured = get_settings().get('image.memory_cache_size', memory_cache_size)
            # 如果配置存在且为数字，则覆盖默认值
            memory_cache_size = int(configured) if configured is not None else memory_cache_size
        except Exception as e:
            logger.debug(f"读取配置 image.memory_cache_size 失败，使用默认值: {e}")

        self.memory_cache_size = memory_cache_size
        self.thumbnail_size = thumbnail_size
        self.thumbnail_quality = thumbnail_quality
        self.max_age_hours = max_age_hours

        # 确定存储目录（支持用户配置）
        self.base_dir = self._resolve_base_dir(base_dir)
        self.thumbnails_dir = ensure_dir(self.base_dir / "thumbnails")

        # 内存缓存：hash -> (base64_data, timestamp)
        self._memory_cache: OrderedDict[str, Tuple[str, datetime]] = OrderedDict()

        self._ensure_directories()

        logger.info(
            f"ImageManager initialized: cache_size={memory_cache_size}, "
            f"thumbnail_size={thumbnail_size}, quality={thumbnail_quality}, base_dir={self.base_dir}"
        )

    def _resolve_base_dir(self, override: Optional[str]) -> Path:
        """根据配置或覆盖参数解析截图根目录"""
        candidates: List[Path] = []

        if override:
            candidates.append(Path(override).expanduser())

        # 尝试读取配置中的自定义路径
        try:
            from core.settings import get_settings

            settings_path = get_settings().get_screenshot_path()
            if settings_path:
                candidates.append(Path(settings_path).expanduser())
        except Exception as exc:
            logger.debug(f"读取截图配置路径失败，使用默认路径: {exc}")

        # 默认回退到 ~/.config/rewind/screenshots
        candidates.append(Path(get_data_dir("screenshots")))

        for candidate in candidates:
            try:
                return ensure_dir(candidate)
            except Exception as exc:
                logger.warning(f"无法使用截图目录 {candidate}: {exc}")

        # 最终兜底
        return ensure_dir(Path(get_data_dir("screenshots")))

    def _ensure_directories(self):
        """确保目录存在"""
        ensure_dir(self.base_dir)
        ensure_dir(self.thumbnails_dir)

    def add_to_memory_cache(self, img_hash: str, img_bytes: bytes) -> str:
        """
        添加图片到内存缓存

        Args:
            img_hash: 图片哈希值
            img_bytes: 原始图片字节数据

        Returns:
            base64编码的图片数据
        """
        try:
            # 如果已经在缓存中，移动到最后（最近使用）
            if img_hash in self._memory_cache:
                self._memory_cache.move_to_end(img_hash)
                return self._memory_cache[img_hash][0]

            # 编码为 base64
            base64_data = base64.b64encode(img_bytes).decode('utf-8')

            # 添加到缓存
            self._memory_cache[img_hash] = (base64_data, datetime.now())

            # 如果超过缓存大小，移除最旧的
            while len(self._memory_cache) > self.memory_cache_size:
                oldest_hash, _ = self._memory_cache.popitem(last=False)
                logger.debug(f"从内存缓存中移除旧图片: {oldest_hash}")

            return base64_data

        except Exception as e:
            logger.error(f"添加图片到内存缓存失败: {e}")
            return ""

    def get_from_memory_cache(self, img_hash: str) -> Optional[str]:
        """
        从内存缓存获取图片

        Args:
            img_hash: 图片哈希值

        Returns:
            base64编码的图片数据，如果不存在返回 None
        """
        if img_hash in self._memory_cache:
            # 移动到最后（标记为最近使用）
            self._memory_cache.move_to_end(img_hash)
            return self._memory_cache[img_hash][0]
        return None

    def get_multiple_from_cache(self, img_hashes: list[str]) -> dict[str, str]:
        """
        批量从内存缓存获取图片

        Args:
            img_hashes: 图片哈希值列表

        Returns:
            dict: {hash: base64_data}
        """
        result = {}
        for img_hash in img_hashes:
            data = self.get_from_memory_cache(img_hash)
            if data:
                result[img_hash] = data
        return result

    def create_thumbnail(self, img_bytes: bytes, img_hash: str) -> Tuple[str, int]:
        """
        创建缩略图并保存到磁盘

        Args:
            img_bytes: 原始图片字节数据
            img_hash: 图片哈希值

        Returns:
            (缩略图文件路径, 文件大小)
        """
        try:
            # 加载图片
            img = Image.open(io.BytesIO(img_bytes))

            # 转换为 RGB（如果需要）
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 生成缩略图（保持宽高比）
            img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

            # 生成文件名
            filename = f"thumb_{img_hash[:12]}.jpg"
            file_path = self.thumbnails_dir / filename

            # 保存缩略图
            img.save(file_path, format='JPEG', quality=self.thumbnail_quality, optimize=True)

            # 获取文件大小
            file_size = file_path.stat().st_size

            logger.debug(
                f"缩略图已创建: {filename}, "
                f"尺寸={img.size}, 大小={file_size/1024:.1f}KB"
            )

            return str(file_path), file_size

        except Exception as e:
            logger.error(f"创建缩略图失败: {e}")
            return "", 0

    def persist_image(self, img_hash: str, img_bytes: bytes, keep_original: bool = False) -> Dict[str, any]:
        """
        持久化图片（只保存缩略图，可选保留原图）

        Args:
            img_hash: 图片哈希值
            img_bytes: 原始图片字节数据
            keep_original: 是否保留原图

        Returns:
            包含缩略图路径和大小信息的字典
        """
        try:
            # 创建缩略图
            thumbnail_path, thumbnail_size = self.create_thumbnail(img_bytes, img_hash)

            if not thumbnail_path:
                return {"success": False, "error": "Failed to create thumbnail"}

            result: Dict[str, any] = {
                "success": True,
                "thumbnail_path": thumbnail_path,
                "thumbnail_size": thumbnail_size,
                "hash": img_hash
            }

            # 如果需要保留原图
            if keep_original:
                original_filename = f"orig_{img_hash[:12]}.jpg"
                original_path = ensure_dir(self.base_dir / "originals") / original_filename

                with open(original_path, 'wb') as f:
                    f.write(img_bytes)

                result["original_path"] = str(original_path)
                result["original_size"] = len(img_bytes)

            # 从内存缓存中移除（已持久化）
            self._memory_cache.pop(img_hash, None)

            return result

        except Exception as e:
            logger.error(f"持久化图片失败: {e}")
            return {"success": False, "error": str(e)}

    def get_thumbnail_path(self, img_hash: str) -> str:
        """根据哈希获取缩略图路径"""
        if not img_hash:
            return ""
        filename = f"thumb_{img_hash[:12]}.jpg"
        return str(self.thumbnails_dir / filename)

    def load_thumbnail_base64(self, img_hash: str) -> Optional[str]:
        """从磁盘加载缩略图并返回 base64 数据"""
        try:
            thumbnail_path = self.get_thumbnail_path(img_hash)
            if not thumbnail_path:
                return None
            path = Path(thumbnail_path)
            if not path.exists():
                return None

            with path.open("rb") as f:
                data = f.read()
            return base64.b64encode(data).decode("utf-8")
        except Exception as e:
            logger.error(f"加载缩略图失败: {e}")
            return None

    def cleanup_old_files(self, max_age_hours: Optional[int] = None) -> int:
        """
        清理旧的临时文件

        Args:
            max_age_hours: 文件最大保留时间（小时），None 则使用默认值

        Returns:
            清理的文件数量
        """
        try:
            max_age = max_age_hours or self.max_age_hours
            cutoff_time = datetime.now() - timedelta(hours=max_age)
            cutoff_timestamp = cutoff_time.timestamp()

            cleaned_count = 0
            total_size = 0

            for file_path in self.thumbnails_dir.glob("*"):
                if not file_path.is_file():
                    continue

                if file_path.stat().st_mtime < cutoff_timestamp:
                    file_size = file_path.stat().st_size
                    file_path.unlink(missing_ok=True)
                    cleaned_count += 1
                    total_size += file_size
                    logger.debug(f"已删除旧文件: {file_path.name}")

            if cleaned_count > 0:
                logger.info(
                    f"清理了 {cleaned_count} 个旧文件, "
                    f"释放空间: {total_size/1024/1024:.2f}MB"
                )

            return cleaned_count

        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, any]:
        """获取缓存统计信息"""
        try:
            # 内存缓存统计
            memory_count = len(self._memory_cache)

            # 磁盘统计
            disk_count = 0
            disk_size = 0

            if self.thumbnails_dir.exists():
                for file_path in self.thumbnails_dir.glob("*"):
                    if file_path.is_file():
                        disk_count += 1
                        disk_size += file_path.stat().st_size

            return {
                "memory_cache_count": memory_count,
                "memory_cache_limit": self.memory_cache_size,
                "disk_thumbnail_count": disk_count,
                "disk_total_size_mb": disk_size / 1024 / 1024,
                "thumbnail_size": self.thumbnail_size,
                "thumbnail_quality": self.thumbnail_quality
            }

        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}

    def clear_memory_cache(self) -> int:
        """清空内存缓存"""
        count = len(self._memory_cache)
        self._memory_cache.clear()
        logger.info(f"已清空内存缓存: {count} 个图片")
        return count

    def estimate_compression_savings(self, img_bytes: bytes) -> Dict[str, any]:
        """
        估算压缩后的空间节省

        Args:
            img_bytes: 原始图片字节数据

        Returns:
            包含原始大小、缩略图大小和节省比例的字典
        """
        try:
            original_size = len(img_bytes)

            # 创建临时缩略图以估算大小
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

            # 压缩到内存中
            thumb_bytes = io.BytesIO()
            img.save(thumb_bytes, format='JPEG', quality=self.thumbnail_quality, optimize=True)
            thumbnail_size = len(thumb_bytes.getvalue())

            savings_ratio = (1 - thumbnail_size / original_size) * 100

            return {
                "original_size_kb": original_size / 1024,
                "thumbnail_size_kb": thumbnail_size / 1024,
                "savings_ratio": savings_ratio,
                "space_saved_kb": (original_size - thumbnail_size) / 1024
            }

        except Exception as e:
            logger.error(f"估算压缩节省失败: {e}")
            return {}

    def update_storage_path(self, new_base_dir: str) -> None:
        """更新截图存储路径（响应配置变更）"""
        if not new_base_dir:
            return

        try:
            resolved = ensure_dir(Path(new_base_dir).expanduser())
            if resolved == self.base_dir:
                return

            self.base_dir = resolved
            self.thumbnails_dir = ensure_dir(self.base_dir / "thumbnails")

            logger.info(f"截图存储目录已更新: {self.base_dir}")
        except Exception as exc:
            logger.error(f"更新截图存储目录失败: {exc}")


# 全局单例
_image_manager: Optional[ImageManager] = None


def get_image_manager() -> ImageManager:
    """获取图片管理器单例"""
    global _image_manager
    if _image_manager is None:
        _image_manager = ImageManager()
    return _image_manager


def init_image_manager(**kwargs) -> ImageManager:
    """初始化图片管理器（可自定义参数）"""
    global _image_manager
    _image_manager = ImageManager(**kwargs)
    return _image_manager
