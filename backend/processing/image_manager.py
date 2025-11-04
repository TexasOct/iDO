"""
Image manager
Manages screenshot memory cache, thumbnail generation, compression and persistence strategies
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
    """Image manager - Manages screenshot memory cache and persistence"""

    def __init__(
        self,
        memory_cache_size: int = 500,  # Maximum number of images to keep in memory (default increased to 500, can be overridden by configuration)
        thumbnail_size: Tuple[int, int] = (
            400,
            225,
        ),  # Thumbnail size (16:9 aspect ratio)
        thumbnail_quality: int = 75,  # Thumbnail quality
        max_age_hours: int = 24,  # Maximum retention time for temporary files
        base_dir: Optional[
            str
        ] = None,  # Screenshot storage root directory (override config)
    ):
        # Try to read custom path from configuration
        try:
            from core.settings import get_settings

            configured = get_settings().get(
                "image.memory_cache_size", memory_cache_size
            )
            # Override default value if configuration exists and is numeric
            memory_cache_size = (
                int(configured) if configured is not None else memory_cache_size
            )
        except Exception as e:
            logger.debug(
                f"Failed to read config image.memory_cache_size, using default value: {e}"
            )

        self.memory_cache_size = memory_cache_size
        self.thumbnail_size = thumbnail_size
        self.thumbnail_quality = thumbnail_quality
        self.max_age_hours = max_age_hours

        # Determine storage directory (supports user configuration)
        self.base_dir = self._resolve_base_dir(base_dir)
        self.thumbnails_dir = ensure_dir(self.base_dir / "thumbnails")

        # Memory cache: hash -> (base64_data, timestamp)
        self._memory_cache: OrderedDict[str, Tuple[str, datetime]] = OrderedDict()

        self._ensure_directories()

        logger.info(
            f"ImageManager initialized: cache_size={memory_cache_size}, "
            f"thumbnail_size={thumbnail_size}, quality={thumbnail_quality}, base_dir={self.base_dir}"
        )

    def _resolve_base_dir(self, override: Optional[str]) -> Path:
        """Parse screenshot root directory based on configuration or override parameter"""
        candidates: List[Path] = []

        if override:
            candidates.append(Path(override).expanduser())

        # Try to read custom path from configuration
        try:
            from core.settings import get_settings

            config_path = get_settings().get("image_storage_path", "")
            if config_path:
                candidates.append(Path(config_path).expanduser())
        except Exception:
            logger.debug("Could not read image_storage_path from settings")

        # Use configured data directory as fallback
        candidates.append(get_data_dir() / "screenshots")

        # Use first valid candidate
        for candidate in candidates:
            if candidate.exists() or candidate.parent.exists():
                return ensure_dir(candidate)

        # If none exist, use the data directory (it will be created)
        return ensure_dir(candidates[-1])

    def _ensure_directories(self):
        """Ensure required directories exist"""
        ensure_dir(self.thumbnails_dir)

    def get_from_cache(self, img_hash: str) -> Optional[str]:
        """Get image from memory cache

        Args:
            img_hash: Image hash value

        Returns:
            base64-encoded image data, return None if not found
        """
        try:
            data, timestamp = self._memory_cache.get(img_hash, (None, None))
            if data:
                # Update access time (move to end)
                self._memory_cache.move_to_end(img_hash)
                return data
        except Exception as e:
            logger.error(f"Failed to get image from cache: {e}")
        return None

    def get_multiple_from_cache(self, img_hashes: List[str]) -> Dict[str, str]:
        """Batch retrieve images from memory cache

        Args:
            img_hashes: List of image hash values

        Returns:
            dict: {hash: base64_data}
        """
        result = {}
        for img_hash in img_hashes:
            data = self.get_from_cache(img_hash)
            if data:
                result[img_hash] = data
        return result

    def add_to_cache(self, img_hash: str, img_data: str) -> None:
        """Add image to memory cache

        Args:
            img_hash: Image hash value
            img_data: base64-encoded image data
        """
        try:
            now = datetime.now()
            self._memory_cache[img_hash] = (img_data, now)

            # Remove oldest entries if cache is full
            while len(self._memory_cache) > self.memory_cache_size:
                self._memory_cache.popitem(last=False)  # Remove oldest

            logger.debug(f"Added image to cache: {img_hash[:8]}...")
        except Exception as e:
            logger.error(f"Failed to add image to cache: {e}")

    def load_thumbnail_base64(self, img_hash: str) -> Optional[str]:
        """Load thumbnail and return base64 data

        Args:
            img_hash: Image hash value

        Returns:
            base64-encoded thumbnail data, return None if not found
        """
        try:
            thumbnail_path = self.thumbnails_dir / f"{img_hash}.jpg"
            if thumbnail_path.exists():
                with open(thumbnail_path, "rb") as f:
                    img_bytes = f.read()
                    return base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            logger.debug(f"Failed to load thumbnail: {e}")
        return None

    def save_thumbnail(self, img_hash: str, thumbnail_bytes: bytes) -> None:
        """Save thumbnail to disk

        Args:
            img_hash: Image hash value
            thumbnail_bytes: Thumbnail image bytes
        """
        try:
            thumbnail_path = self.thumbnails_dir / f"{img_hash}.jpg"
            with open(thumbnail_path, "wb") as f:
                f.write(thumbnail_bytes)
            logger.debug(f"Saved thumbnail: {thumbnail_path}")
        except Exception as e:
            logger.error(f"Failed to save thumbnail: {e}")

    def _create_thumbnail(self, img_bytes: bytes) -> bytes:
        """Create thumbnail from image bytes

        Args:
            img_bytes: Original image bytes

        Returns:
            Thumbnail image bytes
        """
        try:
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")

            img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

            thumb_bytes = io.BytesIO()
            img.save(
                thumb_bytes,
                format="JPEG",
                quality=self.thumbnail_quality,
                optimize=True,
            )
            return thumb_bytes.getvalue()
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            return img_bytes  # Return original if thumbnail creation fails

    def process_image_for_cache(self, img_hash: str, img_bytes: bytes) -> None:
        """Process image: create thumbnail and add to cache

        Args:
            img_hash: Image hash value
            img_bytes: Original image bytes
        """
        try:
            # Create thumbnail
            thumbnail_bytes = self._create_thumbnail(img_bytes)

            # Save thumbnail to disk
            self.save_thumbnail(img_hash, thumbnail_bytes)

            # Add original image to cache
            base64_data = base64.b64encode(img_bytes).decode("utf-8")
            self.add_to_cache(img_hash, base64_data)

            logger.debug(f"Processed image for cache: {img_hash[:8]}...")
        except Exception as e:
            logger.error(f"Failed to process image for cache: {e}")

    def cleanup_old_files(self, max_age_hours: Optional[int] = None) -> int:
        """
        Clean up old temporary files

        Args:
            max_age_hours: Maximum file retention time (hours), None uses default value

        Returns:
            Number of cleaned files
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
                    logger.debug(f"Deleted old file: {file_path.name}")

            if cleaned_count > 0:
                logger.info(
                    f"Cleaned up {cleaned_count} old files, "
                    f"Released space: {total_size / 1024 / 1024:.2f}MB"
                )

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to clean up old files: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            # Memory cache stats
            memory_count = len(self._memory_cache)
            memory_size_mb = (
                sum(len(data[0]) for data in self._memory_cache.values()) / 1024 / 1024
            )

            # Disk stats
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
                "memory_cache_size_mb": round(memory_size_mb, 2),
                "disk_thumbnail_count": disk_count,
                "disk_total_size_mb": disk_size / 1024 / 1024,
                "thumbnail_size": self.thumbnail_size,
                "thumbnail_quality": self.thumbnail_quality,
            }

        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {}

    def estimate_compression_savings(self, img_bytes: bytes) -> Dict[str, Any]:
        """
        Estimate space savings after compression

        Args:
            img_bytes: Original image byte data

        Returns:
            Dictionary containing original size, thumbnail size, and savings ratio
        """
        try:
            original_size = len(img_bytes)

            # Create temporary thumbnail to estimate size
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")

            img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

            # Compress to memory
            thumb_bytes = io.BytesIO()
            img.save(
                thumb_bytes,
                format="JPEG",
                quality=self.thumbnail_quality,
                optimize=True,
            )
            thumbnail_size = len(thumb_bytes.getvalue())

            savings_ratio = (1 - thumbnail_size / original_size) * 100

            return {
                "original_size_kb": original_size / 1024,
                "thumbnail_size_kb": thumbnail_size / 1024,
                "savings_ratio": savings_ratio,
                "space_saved_kb": (original_size - thumbnail_size) / 1024,
            }

        except Exception as e:
            logger.error(f"Failed to estimate compression savings: {e}")
            return {}

    def update_storage_path(self, new_base_dir: str) -> None:
        """Update screenshot storage path (respond to configuration changes)"""
        if not new_base_dir:
            return

        try:
            resolved = ensure_dir(Path(new_base_dir).expanduser())
            if resolved == self.base_dir:
                return

            self.base_dir = resolved
            self.thumbnails_dir = ensure_dir(self.base_dir / "thumbnails")

            logger.info(f"Screenshot storage directory updated: {self.base_dir}")
        except Exception as exc:
            logger.error(f"Failed to update screenshot storage directory: {exc}")


# Global singleton
_image_manager: Optional[ImageManager] = None


def get_image_manager() -> ImageManager:
    """Get image manager singleton"""
    global _image_manager
    if _image_manager is None:
        _image_manager = ImageManager()
    return _image_manager


def init_image_manager(**kwargs) -> ImageManager:
    """Initialize image manager (can customize parameters)"""
    global _image_manager
    _image_manager = ImageManager(**kwargs)
    return _image_manager
