"""
Advanced image compression module - further reduce image size and token consumption

Implementation strategies:
1. Dynamic quality adjustment - dynamically adjust JPEG quality based on content importance
2. Adaptive resolution - adjust resolution based on image complexity
3. Smart region cropping - only keep changed regions
4. Multi-level fallback strategy - provide different compression levels for different scenarios
"""

import io
import base64
import numpy as np
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageFilter
from core.logger import get_logger

logger = get_logger(__name__)


class ImageImportanceAnalyzer:
    """Image importance analyzer - determine information density and importance of images"""

    def __init__(self):
        self.stats = {"high_importance": 0, "medium_importance": 0, "low_importance": 0}

    def analyze_importance(self, img_bytes: bytes) -> str:
        """
        Analyze image importance

        Returns:
            'high', 'medium', 'low'
        """
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            # Calculate multiple metrics
            contrast = self._calculate_contrast(img)
            complexity = self._calculate_complexity(img)
            edge_density = self._calculate_edge_density(img)

            # Comprehensive score (0-100)
            score = contrast * 0.4 + complexity * 0.3 + edge_density * 0.3

            # Classification
            if score > 60:
                self.stats["high_importance"] += 1
                return "high"
            elif score > 30:
                self.stats["medium_importance"] += 1
                return "low"
            else:
                self.stats["low_importance"] += 1
                return "low"

        except Exception as e:
            logger.warning(f"Failed to analyze image importance: {e}")
            return "medium"  # Default to medium

    def _calculate_contrast(self, img: Image.Image) -> float:
        """Calculate contrast (0-100)"""
        gray = img.convert("L")
        pixels = np.array(gray, dtype=np.float32)
        std = float(np.std(pixels))
        # Normalize to 0-100
        return min(100, std / 2.55)

    def _calculate_complexity(self, img: Image.Image) -> float:
        """Calculate image complexity (0-100), based on color variation"""
        small = img.resize((32, 32), Image.Resampling.LANCZOS)
        pixels = np.array(small, dtype=np.float32)

        # Calculate pixel differences
        diff_h = np.abs(np.diff(pixels, axis=0)).mean()
        diff_v = np.abs(np.diff(pixels, axis=1)).mean()

        complexity = (diff_h + diff_v) / 2
        # Normalize to 0-100
        return min(100, complexity / 2.55)

    def _calculate_edge_density(self, img: Image.Image) -> float:
        """Calculate edge density (0-100)"""
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_pixels = np.array(edges, dtype=np.float32)

        # Edge pixel ratio
        edge_ratio = (edge_pixels > 50).sum() / edge_pixels.size

        # Normalize to 0-100
        return min(100, edge_ratio * 500)


class DynamicImageCompressor:
    """Dynamic image compressor - adjust compression parameters based on importance"""

    # Compression level definitions
    COMPRESSION_LEVELS = {
        "ultra": {
            "high": {
                "quality": 50,
                "max_size": (600, 400),
                "description": "Ultra aggressive",
            },
            "medium": {
                "quality": 40,
                "max_size": (480, 320),
                "description": "Ultra aggressive",
            },
            "low": {
                "quality": 30,
                "max_size": (400, 300),
                "description": "Ultra aggressive",
            },
        },
        "aggressive": {
            "high": {
                "quality": 60,
                "max_size": (800, 600),
                "description": "Aggressive",
            },
            "medium": {
                "quality": 50,
                "max_size": (640, 480),
                "description": "Aggressive",
            },
            "low": {"quality": 40, "max_size": (480, 360), "description": "Aggressive"},
        },
        "balanced": {
            "high": {"quality": 75, "max_size": (1280, 720), "description": "Balanced"},
            "medium": {
                "quality": 65,
                "max_size": (960, 540),
                "description": "Balanced",
            },
            "low": {"quality": 55, "max_size": (800, 450), "description": "Balanced"},
        },
        "quality": {
            "high": {
                "quality": 85,
                "max_size": (1920, 1080),
                "description": "Quality priority",
            },
            "medium": {
                "quality": 80,
                "max_size": (1600, 900),
                "description": "Quality priority",
            },
            "low": {
                "quality": 75,
                "max_size": (1280, 720),
                "description": "Quality priority",
            },
        },
    }

    def __init__(self, compression_level: str = "aggressive"):
        """
        Args:
            compression_level: 'ultra', 'aggressive', 'balanced', 'quality'
        """
        self.compression_level = compression_level
        self.importance_analyzer = ImageImportanceAnalyzer()
        self.stats = {
            "original_size": 0,
            "compressed_size": 0,
            "compression_ratio": 0.0,
            "images_processed": 0,
        }

    def compress(
        self, img_bytes: bytes, force_importance: Optional[str] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress image

        Args:
            img_bytes: Original image bytes
            force_importance: Force specify importance level (optional)

        Returns:
            (compressed_bytes, metadata)
        """
        try:
            original_size = len(img_bytes)
            self.stats["original_size"] += original_size
            self.stats["images_processed"] += 1

            # Analyze importance
            importance = (
                force_importance
                or self.importance_analyzer.analyze_importance(img_bytes)
            )

            # Get compression parameters
            params = self.COMPRESSION_LEVELS[self.compression_level][importance]
            quality = params["quality"]
            max_size = params["max_size"]

            # Open image
            img = Image.open(io.BytesIO(img_bytes))
            original_dimensions = img.size

            # Adjust resolution
            img = self._resize_smart(img, max_size)

            # Convert color space optimization
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            # Compress
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            compressed_bytes = output.getvalue()

            compressed_size = len(compressed_bytes)
            self.stats["compressed_size"] += compressed_size

            # Calculate compression ratio
            compression_ratio = (
                compressed_size / original_size if original_size > 0 else 1.0
            )

            metadata = {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "size_reduction": 1 - compression_ratio,
                "original_dimensions": original_dimensions,
                "final_dimensions": img.size,
                "quality": quality,
                "importance": importance,
                "compression_level": self.compression_level,
            }

            logger.debug(
                f"Image compression: {original_dimensions[0]}x{original_dimensions[1]} → "
                f"{img.size[0]}x{img.size[1]}, "
                f"{original_size / 1024:.1f}KB → {compressed_size / 1024:.1f}KB "
                f"({compression_ratio * 100:.1f}%), "
                f"importance: {importance}, quality: {quality}"
            )

            return compressed_bytes, metadata

        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            # Return original image on failure
            return img_bytes, {"error": str(e), "compression_ratio": 1.0}

    def _resize_smart(self, img: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
        """
        Smart resize image while maintaining aspect ratio

        Args:
            img: PIL Image
            max_size: (max_width, max_height)

        Returns:
            Resized image
        """
        width, height = img.size
        max_width, max_height = max_size

        # If already smaller than target size, don't resize
        if width <= max_width and height <= max_height:
            return img

        # Calculate scaling ratio while maintaining aspect ratio
        ratio_w = max_width / width
        ratio_h = max_height / height
        ratio = min(ratio_w, ratio_h)

        new_width = int(width * ratio)
        new_height = int(height * ratio)

        # Use LANCZOS to ensure quality
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

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
            "space_saved_mb": (
                self.stats["original_size"] - self.stats["compressed_size"]
            )
            / (1024 * 1024),
            "importance_distribution": self.importance_analyzer.stats,
        }


class RegionCropper:
    """Smart region cropper - only keeps changed regions"""

    def __init__(self, diff_threshold: int = 30, min_region_size: int = 100):
        """
        Args:
            diff_threshold: Pixel difference threshold (0-255)
            min_region_size: Minimum region size (pixels)
        """
        self.diff_threshold = diff_threshold
        self.min_region_size = min_region_size
        self.last_image = None
        self.stats = {"full_images": 0, "cropped_images": 0, "total_crop_ratio": 0.0}

    def crop_changed_region(
        self, img_bytes: bytes, force_full: bool = False
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Crop to only contain changed regions

        Args:
            img_bytes: Current image bytes
            force_full: Force using full image (no cropping)

        Returns:
            (cropped_bytes, metadata)
        """
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            # First image or force full
            if self.last_image is None or force_full:
                self.last_image = img
                self.stats["full_images"] += 1

                return img_bytes, {
                    "is_cropped": False,
                    "crop_ratio": 1.0,
                    "reason": "first_image",
                }

            # Calculate differences
            bbox = self._find_diff_bbox(self.last_image, img)

            if bbox is None:
                # No significant difference, return original image
                self.stats["full_images"] += 1
                return img_bytes, {
                    "is_cropped": False,
                    "crop_ratio": 1.0,
                    "reason": "no_significant_change",
                }

            # Crop changed region
            cropped = img.crop(bbox)

            # Check if cropped region is too small
            crop_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            full_area = img.width * img.height
            crop_ratio = crop_area / full_area

            if crop_ratio > 0.8:
                # Changed region too large, keep full image
                self.last_image = img
                self.stats["full_images"] += 1
                return img_bytes, {
                    "is_cropped": False,
                    "crop_ratio": crop_ratio,
                    "reason": "change_too_large",
                }

            # Save cropped image
            output = io.BytesIO()
            cropped.save(output, format="JPEG", quality=85)
            cropped_bytes = output.getvalue()

            # Update statistics
            self.last_image = img
            self.stats["cropped_images"] += 1
            self.stats["total_crop_ratio"] += crop_ratio

            metadata = {
                "is_cropped": True,
                "crop_ratio": crop_ratio,
                "original_size": img.size,
                "cropped_size": cropped.size,
                "bbox": bbox,
                "size_reduction": 1 - (len(cropped_bytes) / len(img_bytes)),
            }

            logger.debug(
                f"Region cropping: {img.size[0]}x{img.size[1]} → "
                f"{cropped.size[0]}x{cropped.size[1]} "
                f"({crop_ratio * 100:.1f}% retained)"
            )

            return cropped_bytes, metadata

        except Exception as e:
            logger.error(f"Region cropping failed: {e}")
            return img_bytes, {"is_cropped": False, "error": str(e)}

    def _find_diff_bbox(
        self, img1: Image.Image, img2: Image.Image
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the boundary of different regions between two images

        Returns:
            (left, top, right, bottom) or None
        """
        try:
            # Ensure same size
            if img1.size != img2.size:
                return None

            # Convert to numpy arrays
            arr1 = np.array(img1, dtype=np.float32)
            arr2 = np.array(img2, dtype=np.float32)

            # Calculate pixel differences
            diff = np.abs(arr1 - arr2).mean(axis=2)  # Average RGB difference

            # Binarize difference map
            changed = diff > self.diff_threshold

            # Find boundaries of changed regions
            rows = np.any(changed, axis=1)
            cols = np.any(changed, axis=0)

            if not rows.any() or not cols.any():
                return None

            top = np.argmax(rows)
            bottom = len(rows) - np.argmax(rows[::-1])
            left = np.argmax(cols)
            right = len(cols) - np.argmax(cols[::-1])

            # Add margin
            margin = 10
            width, height = img1.size

            left = max(0, left - margin)
            top = max(0, top - margin)
            right = min(width, right + margin)
            bottom = min(height, bottom + margin)

            # Check region size
            region_width = right - left
            region_height = bottom - top

            if (
                region_width < self.min_region_size
                or region_height < self.min_region_size
            ):
                return None

            return (left, top, right, bottom)

        except Exception as e:
            logger.warning(f"Failed to calculate difference boundary: {e}")
            return None

    def reset(self):
        """Reset state"""
        self.last_image = None

    def get_stats(self) -> Dict[str, Any]:
        """Get cropping statistics"""
        total_images = self.stats["full_images"] + self.stats["cropped_images"]
        avg_crop_ratio = (
            self.stats["total_crop_ratio"] / self.stats["cropped_images"]
            if self.stats["cropped_images"] > 0
            else 1.0
        )

        return {
            "total_images": total_images,
            "full_images": self.stats["full_images"],
            "cropped_images": self.stats["cropped_images"],
            "crop_percentage": (
                self.stats["cropped_images"] / total_images * 100
                if total_images > 0
                else 0
            ),
            "average_crop_ratio": avg_crop_ratio,
            "average_size_reduction": 1 - avg_crop_ratio,
        }


class AdvancedImageOptimizer:
    """
    Advanced image optimizer - comprehensive use of compression and cropping

    Workflow:
    1. Analyze image importance
    2. Dynamic compression based on importance
    3. (Optional) Crop changed regions
    4. Record detailed statistics
    """

    def __init__(
        self,
        compression_level: str = "aggressive",
        enable_cropping: bool = False,
        crop_threshold: int = 30,
    ):
        """
        Args:
            compression_level: Compression level ('ultra', 'aggressive', 'balanced', 'quality')
            enable_cropping: Whether to enable region cropping
            crop_threshold: Cropping difference threshold
        """
        self.compressor = DynamicImageCompressor(compression_level)
        self.cropper = (
            RegionCropper(diff_threshold=crop_threshold) if enable_cropping else None
        )
        self.enable_cropping = enable_cropping
        self.stats = {
            "images_processed": 0,
            "total_original_tokens": 0,
            "total_optimized_tokens": 0,
        }

    def optimize(
        self, img_bytes: bytes, is_first: bool = False
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Optimize image

        Args:
            img_bytes: Original image bytes
            is_first: Whether this is the first image (first image is not cropped)

        Returns:
            (optimized_bytes, metadata)
        """
        try:
            original_size = len(img_bytes)

            # Estimate original token count (assume 1KB ≈ 85 tokens)
            original_tokens = int(original_size / 1024 * 85)
            self.stats["total_original_tokens"] += original_tokens

            # Step 1: Region cropping (optional)
            if self.enable_cropping and self.cropper:
                img_bytes, crop_meta = self.cropper.crop_changed_region(
                    img_bytes, force_full=is_first
                )
            else:
                crop_meta = {"is_cropped": False}

            # Step 2: Dynamic compression
            compressed_bytes, compress_meta = self.compressor.compress(img_bytes)

            # Estimate optimized token count
            optimized_tokens = int(len(compressed_bytes) / 1024 * 85)
            self.stats["total_optimized_tokens"] += optimized_tokens
            self.stats["images_processed"] += 1

            # Comprehensive metadata
            metadata = {
                "original_size": original_size,
                "final_size": len(compressed_bytes),
                "total_reduction": 1 - (len(compressed_bytes) / original_size),
                "original_tokens": original_tokens,
                "optimized_tokens": optimized_tokens,
                "tokens_saved": original_tokens - optimized_tokens,
                "cropping": crop_meta,
                "compression": compress_meta,
            }

            logger.debug(
                f"Image optimization completed: {original_size / 1024:.1f}KB → {len(compressed_bytes) / 1024:.1f}KB, "
                f"Token: {original_tokens} → {optimized_tokens} "
                f"(saved {metadata['tokens_saved']})"
            )

            return compressed_bytes, metadata

        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            return img_bytes, {"error": str(e), "total_reduction": 0}

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        compression_stats = self.compressor.get_stats()
        cropping_stats = self.cropper.get_stats() if self.cropper else {}

        token_reduction = (
            1
            - (
                self.stats["total_optimized_tokens"]
                / self.stats["total_original_tokens"]
            )
            if self.stats["total_original_tokens"] > 0
            else 0
        )

        return {
            "images_processed": self.stats["images_processed"],
            "tokens": {
                "original": self.stats["total_original_tokens"],
                "optimized": self.stats["total_optimized_tokens"],
                "saved": self.stats["total_original_tokens"]
                - self.stats["total_optimized_tokens"],
                "reduction_percentage": token_reduction * 100,
            },
            "compression": compression_stats,
            "cropping": cropping_stats,
        }

    def reset(self):
        """Reset all states"""
        if self.cropper:
            self.cropper.reset()
        self.stats = {
            "images_processed": 0,
            "total_original_tokens": 0,
            "total_optimized_tokens": 0,
        }

    def reinitialize(
        self,
        compression_level: str = "aggressive",
        enable_cropping: bool = False,
        crop_threshold: int = 30,
    ):
        """Reinitialize optimizer configuration (for dynamic configuration updates)

        Args:
            compression_level: Compression level
            enable_cropping: Whether to enable region cropping
            crop_threshold: Cropping threshold percentage
        """
        # Recreate compressor
        self.compressor = DynamicImageCompressor(compression_level)

        # Recreate cropper (if needed)
        if self.enable_cropping and enable_cropping:
            self.cropper = RegionCropper(diff_threshold=crop_threshold)
        else:
            self.cropper = None

        # Reset statistics
        self.reset()

        logger.info(
            f"Image optimizer has been reinitialized: level={compression_level}, cropping={enable_cropping}"
        )


# Global singleton
_global_image_optimizer: Optional[AdvancedImageOptimizer] = None


def get_image_optimizer(reset: bool = False) -> AdvancedImageOptimizer:
    """Get or create global image optimizer instance"""
    global _global_image_optimizer

    if _global_image_optimizer is None or reset:
        try:
            from core.settings import get_settings

            settings = get_settings()

            # Try to get configuration
            config = settings.get_image_optimization_config()
            compression_level = config.get("compression_level", "aggressive")
            enable_cropping = config.get("enable_region_cropping", False)
            crop_threshold = config.get("crop_threshold", 30)

            _global_image_optimizer = AdvancedImageOptimizer(
                compression_level=compression_level,
                enable_cropping=enable_cropping,
                crop_threshold=crop_threshold,
            )
            logger.info(
                f"Advanced image optimizer initialized: compression={compression_level}, cropping={enable_cropping}"
            )
        except Exception as e:
            logger.debug(
                f"Failed to read parameters from configuration: {e}, using default parameters"
            )
            _global_image_optimizer = AdvancedImageOptimizer()

    return _global_image_optimizer
