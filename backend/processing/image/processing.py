"""
Unified image processing module

Consolidates functionality from:
- image_compression.py (DynamicImageCompressor, RegionCropper, AdvancedImageOptimizer)
- image_optimization.py (ImageDifferenceAnalyzer, EventDensitySampler, HybridImageFilter)

Provides clean, unified interface for:
- Image compression (resolution-based)
- Duplicate detection (perceptual hash)
- Smart sampling (time/quantity limits)
- Region cropping (optional)
"""

import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.logger import get_logger
from PIL import Image

from .analysis import ImageAnalyzer

logger = get_logger(__name__)


class ImageCompressor:
    """
    Dynamic image compressor using adaptive resolution strategy

    Strategy:
    - 4K (3840x2160) → 2K (2560x1440)
    - 2K (2560x1440) → 1080p (1920x1080)
    - < 1080p → no compression
    - Maintains high quality (85) for LLM analysis
    """

    # Resolution thresholds
    RESOLUTION_4K = (3840, 2160)
    RESOLUTION_2K = (2560, 1440)
    RESOLUTION_1080P = (1920, 1080)
    DEFAULT_QUALITY = 85

    def __init__(self):
        self.stats = {
            "original_size": 0,
            "compressed_size": 0,
            "images_processed": 0,
        }

    def compress(self, img_bytes: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress image using dynamic resolution strategy

        Args:
            img_bytes: Original image bytes

        Returns:
            (compressed_bytes, metadata)
        """
        try:
            original_size = len(img_bytes)
            self.stats["original_size"] += original_size
            self.stats["images_processed"] += 1

            # Open image
            img = Image.open(io.BytesIO(img_bytes))
            original_dimensions = img.size
            original_width, original_height = original_dimensions

            # Calculate target resolution
            target_size = self._calculate_target_resolution(
                original_width, original_height
            )

            # Resize if needed
            if target_size != original_dimensions:
                img = self._resize_image(img, target_size)

            # Convert color space
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            # Compress with high quality
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=self.DEFAULT_QUALITY, optimize=True)
            compressed_bytes = output.getvalue()

            compressed_size = len(compressed_bytes)
            self.stats["compressed_size"] += compressed_size

            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0

            metadata = {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "size_reduction": 1 - compression_ratio,
                "original_dimensions": original_dimensions,
                "final_dimensions": img.size,
                "quality": self.DEFAULT_QUALITY,
                "strategy": self._get_strategy_name(original_dimensions, img.size),
            }

            logger.debug(
                f"Compressed: {original_dimensions[0]}x{original_dimensions[1]} → "
                f"{img.size[0]}x{img.size[1]}, "
                f"{original_size / 1024:.1f}KB → {compressed_size / 1024:.1f}KB "
                f"({compression_ratio * 100:.1f}%)"
            )

            return compressed_bytes, metadata

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return img_bytes, {"error": str(e), "compression_ratio": 1.0}

    def _calculate_target_resolution(self, width: int, height: int) -> Tuple[int, int]:
        """Calculate target resolution based on dynamic strategy"""
        total_pixels = width * height

        pixels_4k = self.RESOLUTION_4K[0] * self.RESOLUTION_4K[1]
        pixels_2k = self.RESOLUTION_2K[0] * self.RESOLUTION_2K[1]
        pixels_1080p = self.RESOLUTION_1080P[0] * self.RESOLUTION_1080P[1]

        is_portrait = height > width

        # Determine target based on pixel count
        if total_pixels >= pixels_4k:
            base_target = self.RESOLUTION_2K
        elif total_pixels >= pixels_2k:
            base_target = self.RESOLUTION_1080P
        elif total_pixels > pixels_1080p:
            base_target = self.RESOLUTION_1080P
        else:
            return (width, height)  # No compression needed

        # Handle portrait orientation
        if is_portrait:
            target_resolution = (base_target[1], base_target[0])
        else:
            target_resolution = base_target

        # Fit to target while maintaining aspect ratio
        return self._fit_to_resolution(width, height, target_resolution)

    def _fit_to_resolution(
        self, width: int, height: int, target_res: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Fit image to target resolution maintaining aspect ratio"""
        max_width, max_height = target_res
        aspect_ratio = width / height
        target_aspect = max_width / max_height

        if aspect_ratio > target_aspect:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)

        return (new_width, new_height)

    def _resize_image(self, img: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """Resize image using high quality LANCZOS"""
        return img.resize(target_size, Image.Resampling.LANCZOS)

    def _get_strategy_name(
        self, original: Tuple[int, int], final: Tuple[int, int]
    ) -> str:
        """Get human-readable strategy name"""
        if original == final:
            return "no_compression"

        orig_pixels = original[0] * original[1]
        pixels_4k = self.RESOLUTION_4K[0] * self.RESOLUTION_4K[1]
        pixels_2k = self.RESOLUTION_2K[0] * self.RESOLUTION_2K[1]

        if orig_pixels >= pixels_4k:
            return "4K→2K"
        elif orig_pixels >= pixels_2k:
            return "2K→1080p"
        else:
            return "→1080p"

    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        if self.stats["original_size"] > 0:
            overall_ratio = self.stats["compressed_size"] / self.stats["original_size"]
        else:
            overall_ratio = 1.0

        return {
            "images_processed": self.stats["images_processed"],
            "total_original_size_mb": self.stats["original_size"] / (1024 * 1024),
            "total_compressed_size_mb": self.stats["compressed_size"] / (1024 * 1024),
            "overall_compression_ratio": overall_ratio,
            "overall_size_reduction": 1 - overall_ratio,
            "space_saved_mb": (self.stats["original_size"] - self.stats["compressed_size"]) / (1024 * 1024),
        }


class ImageDuplicateDetector:
    """
    Perceptual hash-based duplicate detector

    Uses perceptual hashing (pHash) to detect similar images
    More effective than MD5 for detecting visually similar screenshots
    """

    def __init__(self, threshold: float = 0.15):
        """
        Args:
            threshold: Change threshold (0-1), higher = more sensitive
        """
        self.threshold = threshold
        self.last_phash: Optional[str] = None
        self.stats = {
            "total_checked": 0,
            "significant_changes": 0,
            "duplicates_skipped": 0,
        }

    def calculate_phash(self, img_bytes: bytes) -> Optional[str]:
        """
        Calculate perceptual hash

        Returns 64-bit binary string representing image structure
        """
        try:
            img = Image.open(io.BytesIO(img_bytes))
            img = img.resize((8, 8), Image.Resampling.LANCZOS)
            pixels: List[int] = list(img.convert("L").getdata())  # type: ignore[arg-type]

            avg = sum(pixels) / len(pixels)
            bits = "".join(["1" if p > avg else "0" for p in pixels])
            return bits

        except Exception as e:
            logger.warning(f"Failed to calculate perceptual hash: {e}")
            return None

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hashes"""
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return 64
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    def is_duplicate(self, img_bytes: bytes) -> bool:
        """
        Check if image is duplicate of previous

        Returns:
            True if duplicate (skip), False if significant change (keep)
        """
        self.stats["total_checked"] += 1

        current_phash = self.calculate_phash(img_bytes)
        if current_phash is None:
            self.stats["significant_changes"] += 1
            self.last_phash = None
            return False

        if self.last_phash is None:
            self.last_phash = current_phash
            self.stats["significant_changes"] += 1
            return False

        distance = self.hamming_distance(self.last_phash, current_phash)
        similarity = 1 - (distance / 64.0)

        is_duplicate = similarity >= (1 - self.threshold)

        if is_duplicate:
            self.stats["duplicates_skipped"] += 1
        else:
            self.stats["significant_changes"] += 1
            self.last_phash = current_phash

        return is_duplicate

    def reset(self):
        """Reset state"""
        self.last_phash = None

    def get_stats(self) -> Dict[str, int]:
        """Get statistics"""
        return self.stats.copy()


class ImageSampler:
    """
    Time and quantity-based image sampler

    Limits images by:
    - Minimum time interval between images
    - Maximum total images per event
    """

    def __init__(self, min_interval: float = 2.0, max_images: int = 8):
        """
        Args:
            min_interval: Minimum seconds between images
            max_images: Maximum images per event
        """
        self.min_interval = min_interval
        self.max_images = max_images
        self.last_sampled_time: Dict[str, float] = {}
        self.images_count: Dict[str, int] = {}
        self.stats = {"interval_throttled": 0, "quota_exceeded": 0}

    def should_sample(
        self, event_id: str, current_time: float, is_significant: bool = False
    ) -> Tuple[bool, str]:
        """
        Determine if image should be sampled

        Args:
            event_id: Event identifier
            current_time: Current timestamp
            is_significant: Whether this is a significant change

        Returns:
            (should_sample, reason)
        """
        current_count = self.images_count.get(event_id, 0)

        # Check quota
        if current_count >= self.max_images:
            self.stats["quota_exceeded"] += 1
            return False, f"Quota reached ({self.max_images})"

        # Significant changes always included (if quota allows)
        if is_significant:
            self.last_sampled_time[event_id] = current_time
            self.images_count[event_id] = current_count + 1
            return True, "Significant change"

        # Check time interval
        last_time = self.last_sampled_time.get(event_id, 0)
        if current_time - last_time >= self.min_interval:
            self.last_sampled_time[event_id] = current_time
            self.images_count[event_id] = current_count + 1
            return True, f"Time interval {current_time - last_time:.1f}s"

        self.stats["interval_throttled"] += 1
        return False, f"Insufficient interval (min {self.min_interval}s)"

    def reset(self):
        """Reset state"""
        self.last_sampled_time = {}
        self.images_count = {}

    def get_stats(self) -> Dict[str, int]:
        """Get statistics"""
        return self.stats.copy()


class ImageProcessor:
    """
    Unified image processor

    Combines all image processing capabilities:
    - Compression (resolution-based)
    - Duplicate detection (perceptual hash)
    - Content analysis (static/motion detection)
    - Smart sampling (time/quantity limits)

    Replaces:
    - AdvancedImageOptimizer (from image_compression.py)
    - HybridImageFilter (from image_optimization.py)
    """

    def __init__(
        self,
        # Compression settings
        enable_compression: bool = True,
        # Duplicate detection settings
        enable_deduplication: bool = True,
        phash_threshold: float = 0.15,
        # Content analysis settings
        enable_content_analysis: bool = True,
        # Sampling settings
        enable_sampling: bool = True,
        min_interval: float = 2.0,
        max_images: int = 8,
    ):
        """
        Args:
            enable_compression: Enable resolution-based compression
            enable_deduplication: Enable perceptual hash deduplication
            phash_threshold: Duplicate detection threshold (0-1)
            enable_content_analysis: Enable static/motion detection
            enable_sampling: Enable time/quantity sampling
            min_interval: Minimum seconds between samples
            max_images: Maximum images per event
        """
        self.enable_compression = enable_compression
        self.enable_deduplication = enable_deduplication
        self.enable_content_analysis = enable_content_analysis
        self.enable_sampling = enable_sampling

        # Initialize components
        self.compressor = ImageCompressor() if enable_compression else None
        self.duplicate_detector = (
            ImageDuplicateDetector(threshold=phash_threshold)
            if enable_deduplication
            else None
        )
        self.content_analyzer = ImageAnalyzer() if enable_content_analysis else None
        self.sampler = (
            ImageSampler(min_interval=min_interval, max_images=max_images)
            if enable_sampling
            else None
        )

        # Statistics
        self.stats: Dict[str, Any] = {
            "images_processed": 0,
            "images_included": 0,
            "images_skipped": 0,
            "skip_reasons": {},
            "total_original_tokens": 0,
            "total_optimized_tokens": 0,
        }

    def should_include_image(
        self,
        img_bytes: bytes,
        event_id: str = "",
        current_time: Optional[float] = None,
        is_first: bool = False,
    ) -> Tuple[bool, str]:
        """
        Determine if image should be included

        This method only filters - it doesn't compress
        Use process_image() for compression + filtering

        Args:
            img_bytes: Image data
            event_id: Event identifier (for sampling)
            current_time: Current timestamp (for sampling)
            is_first: Whether this is first image

        Returns:
            (should_include, reason)
        """
        # First image always included
        if is_first:
            return True, "First image"

        # Check for duplicates
        if self.enable_deduplication and self.duplicate_detector:
            if self.duplicate_detector.is_duplicate(img_bytes):
                return False, "Duplicate"

        # Content analysis
        if self.enable_content_analysis and self.content_analyzer:
            should_include, reason = self.content_analyzer.has_significant_content(
                img_bytes
            )
            if not should_include:
                return False, reason

        # Sampling limits
        if self.enable_sampling and self.sampler and event_id:
            if current_time is None:
                current_time = datetime.now().timestamp()
            should_sample, reason = self.sampler.should_sample(
                event_id, current_time, is_significant=True
            )
            if not should_sample:
                return False, reason

        return True, "Passed all filters"

    def process_image(
        self,
        img_bytes: bytes,
        event_id: str = "",
        current_time: Optional[float] = None,
        is_first: bool = False,
    ) -> Tuple[Optional[bytes], Dict[str, Any]]:
        """
        Process image: filter + compress

        Args:
            img_bytes: Original image data
            event_id: Event identifier
            current_time: Current timestamp
            is_first: Whether this is first image

        Returns:
            (processed_bytes or None if skipped, metadata)
        """
        original_size = len(img_bytes)
        original_tokens = int(original_size / 1024 * 85)
        self.stats["total_original_tokens"] += original_tokens
        self.stats["images_processed"] += 1

        # Check if should include
        should_include, reason = self.should_include_image(
            img_bytes, event_id, current_time, is_first
        )

        if not should_include:
            self.stats["images_skipped"] += 1
            self.stats["skip_reasons"][reason] = (
                self.stats["skip_reasons"].get(reason, 0) + 1
            )
            return None, {
                "skipped": True,
                "reason": reason,
                "original_size": original_size,
            }

        # Compress if enabled
        if self.enable_compression and self.compressor:
            processed_bytes, compress_meta = self.compressor.compress(img_bytes)
        else:
            processed_bytes = img_bytes
            compress_meta = {"compression_ratio": 1.0}

        # Update stats
        self.stats["images_included"] += 1
        optimized_tokens = int(len(processed_bytes) / 1024 * 85)
        self.stats["total_optimized_tokens"] += optimized_tokens

        metadata = {
            "skipped": False,
            "original_size": original_size,
            "final_size": len(processed_bytes),
            "total_reduction": 1 - (len(processed_bytes) / original_size),
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": original_tokens - optimized_tokens,
            "compression": compress_meta,
        }

        return processed_bytes, metadata

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        stats = {
            "images_processed": self.stats["images_processed"],
            "images_included": self.stats["images_included"],
            "images_skipped": self.stats["images_skipped"],
            "skip_reasons": self.stats["skip_reasons"].copy(),
        }

        # Token statistics
        if self.stats["total_original_tokens"] > 0:
            token_reduction = (
                1 - self.stats["total_optimized_tokens"] / self.stats["total_original_tokens"]
            )
            stats["tokens"] = {
                "original": self.stats["total_original_tokens"],
                "optimized": self.stats["total_optimized_tokens"],
                "saved": self.stats["total_original_tokens"] - self.stats["total_optimized_tokens"],
                "reduction_percentage": token_reduction * 100,
            }

        # Component stats
        if self.compressor:
            stats["compression"] = self.compressor.get_stats()
        if self.duplicate_detector:
            stats["deduplication"] = self.duplicate_detector.get_stats()
        if self.content_analyzer:
            stats["content_analysis"] = self.content_analyzer.get_stats()
        if self.sampler:
            stats["sampling"] = self.sampler.get_stats()

        return stats

    def reset(self):
        """Reset all state"""
        if self.duplicate_detector:
            self.duplicate_detector.reset()
        if self.sampler:
            self.sampler.reset()
        if self.content_analyzer:
            self.content_analyzer.reset_stats()

        self.stats = {
            "images_processed": 0,
            "images_included": 0,
            "images_skipped": 0,
            "skip_reasons": {},
            "total_original_tokens": 0,
            "total_optimized_tokens": 0,
        }


# Global singletons for backward compatibility
_global_image_processor: Optional[ImageProcessor] = None
_global_compressor: Optional[ImageCompressor] = None


def get_image_processor(reset: bool = False) -> ImageProcessor:
    """
    Get or create global image processor instance

    This replaces both:
    - get_image_optimizer() from image_compression.py
    - get_image_filter() from image_optimization.py
    """
    global _global_image_processor

    if _global_image_processor is None or reset:
        try:
            from core.settings import get_settings

            settings = get_settings()
            config = settings.get_image_optimization_config()

            _global_image_processor = ImageProcessor(
                enable_compression=True,
                enable_deduplication=True,
                phash_threshold=config.get("phash_threshold", 0.15),
                enable_content_analysis=config.get("enable_content_analysis", True),
                enable_sampling=True,
                min_interval=config.get("min_interval", 2.0),
                max_images=config.get("max_images", 8),
            )
            logger.debug(f"ImageProcessor initialized with config: {config}")

        except Exception as e:
            logger.debug(f"Failed to read config, using defaults: {e}")
            _global_image_processor = ImageProcessor()

    return _global_image_processor


def get_image_compressor(reset: bool = False) -> ImageCompressor:
    """Get standalone compressor (for compression-only use cases)"""
    global _global_compressor

    if _global_compressor is None or reset:
        _global_compressor = ImageCompressor()

    return _global_compressor
