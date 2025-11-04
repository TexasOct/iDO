"""
Image optimization module - Reduce LLM Token consumption

Provides multiple optimization strategies:
1. Smart sampling - Detect image changes based on perceptual hash
2. Content-aware perception - Detect image content types and complexity
3. Event density sampling - Time interval-based sampling
"""

import io
import numpy as np
from typing import Optional, Dict, Any, Tuple
from PIL import Image
from core.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


class ImageDifferenceAnalyzer:
    """Image difference analyzer - Use perceptual hash to detect similarity"""

    def __init__(self, threshold: float = 0.15):
        """
        Args:
            threshold: Change degree threshold (0-1), exceeding this value indicates significant change
                      Low threshold = More aggressive sampling, saves more tokens
                      High threshold = More conservative sampling, retains more details
        """
        self.threshold = threshold
        self.last_phash = None
        self.stats = {
            "total_checked": 0,
            "significant_changes": 0,
            "duplicates_skipped": 0,
        }

    def calculate_phash(self, img_bytes: bytes) -> Optional[str]:
        """
        Calculate perceptual hash (Perceptual Hash)

        Returns similar hash for similar but not identical images
        Better than direct MD5 hash for image deduplication

        Args:
            img_bytes: Image byte data

        Returns:
            64-bit binary string representation of hash, or None if failed
        """
        try:
            img = Image.open(io.BytesIO(img_bytes))
            # Resize to 8×8 for calculation, preserving important brightness information
            img = img.resize((8, 8), Image.Resampling.LANCZOS)
            # Convert to grayscale for comparison
            pixels = list(img.convert("L").getdata())

            # Calculate average brightness
            avg = sum(pixels) / len(pixels)

            # Generate binary string: brightness greater than average is 1, otherwise 0
            bits = "".join(["1" if p > avg else "0" for p in pixels])
            return bits
        except Exception as e:
            logger.warning(f"Failed to calculate perceptual hash: {e}")
            return None

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance - Number of different bits between two binary strings

        Args:
            hash1, hash2: 64-bit binary strings

        Returns:
            Number of different bits (0-64)
        """
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return 64  # Maximum distance, considered completely different
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    def is_significant_change(self, img_bytes: bytes) -> bool:
        """
        Determine if there is significant change

        Returns:
            True: Image has significant change, should be sent to LLM
            False: Image change is small, can be skipped
        """
        self.stats["total_checked"] += 1

        current_phash = self.calculate_phash(img_bytes)
        if current_phash is None:
            # When hash calculation fails, default to considering it as changed (conservative strategy)
            logger.warning(
                "Perceptual hash calculation failed, defaulting to consider as changed"
            )
            self.stats["significant_changes"] += 1
            self.last_phash = None
            return True

        # First image is always considered as changed
        if self.last_phash is None:
            self.last_phash = current_phash
            return True

        # Calculate similarity (0-1, 1 means completely identical)
        distance = self.hamming_distance(self.last_phash, current_phash)
        similarity = 1 - (distance / 64.0)

        # Determine if change exceeds threshold
        has_change = similarity < (1 - self.threshold)

        if has_change:
            self.stats["significant_changes"] += 1
            self.last_phash = current_phash
        else:
            self.stats["duplicates_skipped"] += 1

        return has_change

    def reset(self):
        """Reset state for processing new event sequences"""
        self.last_phash = None
        self.stats = {
            "total_checked": 0,
            "significant_changes": 0,
            "duplicates_skipped": 0,
        }

    def get_stats(self) -> Dict[str, int]:
        """Get statistics information"""
        return self.stats.copy()


class ImageContentAnalyzer:
    """Image content analyzer - Detect image content types and complexity"""

    def __init__(self):
        self.stats = {
            "static_skipped": 0,
            "high_contrast_included": 0,
            "motion_detected": 0,
        }

    def analyze_content(self, img_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze image content features

        Returns:
            Dictionary containing the following fields:
            - contrast: Contrast (0-255)
            - edge_activity: Edge activity level
            - is_static: Whether it's static content
            - has_motion: Whether motion is detected
        """
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("L")
            pixels = np.array(img, dtype=np.float32)

            # Calculate contrast (standard deviation)
            contrast = float(np.std(pixels))

            # Calculate edge activity
            if pixels.size > 1:
                edges = np.abs(np.diff(pixels.flatten()))
                edge_activity = float(np.mean(edges))
            else:
                edge_activity = 0.0

            # Determine features
            is_static = contrast < 30  # Low contrast
            has_motion = edge_activity > 10  # High edge activity

            return {
                "contrast": contrast,
                "edge_activity": edge_activity,
                "is_static": is_static,
                "has_motion": has_motion,
            }
        except Exception as e:
            logger.warning(f"Content analysis failed: {e}")
            return {
                "contrast": 0,
                "edge_activity": 0,
                "is_static": False,
                "has_motion": False,
            }

    def should_include_based_on_content(self, img_bytes: bytes) -> Tuple[bool, str]:
        """
        Determine whether to send to LLM based on content

        Returns:
            (should_include, reason)
        """
        content = self.analyze_content(img_bytes)

        # Rule 1: High contrast = potentially meaningful interface change
        if content["contrast"] > 50:
            self.stats["high_contrast_included"] += 1
            return True, "High contrast content"

        # Rule 2: Motion detected = user is interacting
        if content["has_motion"]:
            self.stats["motion_detected"] += 1
            return True, "Motion detected"

        # Rule 3: Low contrast and no motion = possibly blank/waiting screen
        if content["is_static"] and content["contrast"] < 20:
            self.stats["static_skipped"] += 1
            return False, "Static/blank content"

        return True, "Medium complexity"

    def get_stats(self) -> Dict[str, int]:
        """Get statistics information"""
        return self.stats.copy()


class EventDensitySampler:
    """Event density-based sampler - Sample based on time and quantity limits"""

    def __init__(self, min_interval: float = 2.0, max_images: int = 8):
        """
        Args:
            min_interval: Minimum interval between two images (seconds)
            max_images: Maximum number of images sampled in a single event sequence
        """
        self.min_interval = min_interval
        self.max_images = max_images
        self.last_sampled_time = {}
        self.images_count = {}
        self.stats = {"interval_throttled": 0, "quota_exceeded": 0}

    def should_include_image(
        self, event_id: str, current_time: float, is_significant_change: bool
    ) -> Tuple[bool, str]:
        """
        Determine whether to include this image

        Args:
            event_id: Event ID (for tracking)
            current_time: Current timestamp
            is_significant_change: Whether it's a significant change

        Returns:
            (should_include, reason)
        """
        # Rule 1: If there's significant change, always include
        if is_significant_change:
            current_count = self.images_count.get(event_id, 0)

            # But need to check if quota is exceeded
            if current_count >= self.max_images:
                self.stats["quota_exceeded"] += 1
                return False, f"Quota reached ({self.max_images})"

            self.last_sampled_time[event_id] = current_time
            self.images_count[event_id] = current_count + 1
            return True, "Significant change"

        # Rule 2: Check time interval
        last_time = self.last_sampled_time.get(event_id, 0)
        if current_time - last_time >= self.min_interval:
            current_count = self.images_count.get(event_id, 0)

            # Also check quota
            if current_count >= self.max_images:
                self.stats["quota_exceeded"] += 1
                return False, f"Quota reached ({self.max_images})"

            self.last_sampled_time[event_id] = current_time
            self.images_count[event_id] = current_count + 1
            return True, f"Time interval {current_time - last_time:.1f}s"

        # Rule 3: Insufficient time interval
        self.stats["interval_throttled"] += 1
        return False, f"Insufficient interval {self.min_interval}s"

    def reset(self):
        """Reset state for processing new event sequences"""
        self.last_sampled_time = {}
        self.images_count = {}
        self.stats = {"interval_throttled": 0, "quota_exceeded": 0}

    def get_stats(self) -> Dict[str, int]:
        """Get statistics information"""
        return self.stats.copy()


class ImageOptimizationStats:
    """Image optimization statistics tracker"""

    def __init__(self):
        self.total_images = 0
        self.included_images = 0
        self.skipped_images = 0
        self.skip_reasons = {}
        self.start_time = datetime.now()

    def record_image(self, included: bool, reason: str = ""):
        """Record processing result of one image"""
        self.total_images += 1
        if included:
            self.included_images += 1
        else:
            self.skipped_images += 1
            self.skip_reasons[reason] = self.skip_reasons.get(reason, 0) + 1

    def get_summary(self) -> Dict[str, Any]:
        """Get optimization statistics summary"""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if self.total_images == 0:
            return {
                "total_images": 0,
                "included_images": 0,
                "skipped_images": 0,
                "saving_percentage": 0.0,
                "estimated_tokens_saved": 0,
                "skip_breakdown": {},
            }

        saving_pct = (self.skipped_images / self.total_images) * 100
        # Assume each compressed image is about 120 tokens
        tokens_per_image = 120
        estimated_saved = self.skipped_images * tokens_per_image

        return {
            "total_images": self.total_images,
            "included_images": self.included_images,
            "skipped_images": self.skipped_images,
            "saving_percentage": round(saving_pct, 1),
            "estimated_tokens_saved": estimated_saved,
            "skip_breakdown": self.skip_reasons.copy(),
            "elapsed_seconds": round(elapsed, 2),
        }

    def log_summary(self):
        """Record optimization statistics summary"""
        summary = self.get_summary()
        if summary["total_images"] > 0:
            logger.info(
                f"Image optimization statistics: "
                f"Total {summary['total_images']}, "
                f"Included {summary['included_images']}, "
                f"Skipped {summary['skipped_images']} "
                f"({summary['saving_percentage']:.1f}%), "
                f"Estimated saved {summary['estimated_tokens_saved']} tokens"
            )

            if summary["skip_breakdown"]:
                logger.debug(f"Skip reasons distribution: {summary['skip_breakdown']}")


class HybridImageFilter:
    """
    Hybrid image filter - Comprehensively use multiple optimization strategies

    Combines:
    1. Perceptual hash to detect changes
    2. Content analysis filtering
    3. Time/quantity limits
    """

    def __init__(
        self,
        phash_threshold: float = 0.15,
        min_interval: float = 2.0,
        max_images: int = 8,
        enable_content_analysis: bool = True,
    ):
        """
        Args:
            phash_threshold: Perceptual hash change threshold
            min_interval: Minimum sampling interval (seconds)
            max_images: Maximum number of sampled images
            enable_content_analysis: Whether to enable content analysis
        """
        self.diff_analyzer = ImageDifferenceAnalyzer(threshold=phash_threshold)
        self.content_analyzer = (
            ImageContentAnalyzer() if enable_content_analysis else None
        )
        self.sampler = EventDensitySampler(
            min_interval=min_interval, max_images=max_images
        )
        self.stats = ImageOptimizationStats()
        self.enable_content_analysis = enable_content_analysis

    def should_include_image(
        self,
        img_bytes: bytes,
        event_id: str,
        current_time: float,
        is_first: bool = False,
    ) -> Tuple[bool, str]:
        """
        Comprehensively determine whether to include this image

        Returns:
            (should_include, reason)
        """
        # Rule 1: First image is always included
        if is_first:
            self.stats.record_image(True, "First")
            return True, "First image"

        # Rule 2: Detect duplicates (perceptual hash)
        if not self.diff_analyzer.is_significant_change(img_bytes):
            self.stats.record_image(False, "Duplicate")
            return False, "Duplicate of previous"

        # Rule 3: Content analysis (optional)
        if self.enable_content_analysis and self.content_analyzer:
            should_include, content_reason = (
                self.content_analyzer.should_include_based_on_content(img_bytes)
            )
            if not should_include:
                self.stats.record_image(False, content_reason)
                return False, content_reason

        # Rule 4: Time/quantity limits
        should_include, sampler_reason = self.sampler.should_include_image(
            event_id, current_time, True
        )

        self.stats.record_image(
            should_include, sampler_reason if not should_include else ""
        )
        return should_include, sampler_reason

    def reset(self):
        """Reset state for processing new event sequences"""
        self.diff_analyzer.reset()
        self.sampler.reset()

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get complete statistics summary"""
        return {
            "optimization": self.stats.get_summary(),
            "diff_analyzer": self.diff_analyzer.get_stats(),
            "content_analyzer": self.content_analyzer.get_stats()
            if self.content_analyzer
            else {},
            "sampler": self.sampler.get_stats(),
        }

    def log_summary(self):
        """Record statistics summary"""
        self.stats.log_summary()


# Global singleton
_global_image_filter: Optional[HybridImageFilter] = None


def get_image_filter(reset: bool = False) -> HybridImageFilter:
    """Get or create global image filter instance"""
    global _global_image_filter

    if _global_image_filter is None or reset:
        # Read parameters from configuration (if available)
        try:
            from core.settings import get_settings

            settings = get_settings()
            config = settings.get_image_optimization_config()

            _global_image_filter = HybridImageFilter(
                phash_threshold=config.get("phash_threshold", 0.15),
                min_interval=config.get("min_interval", 2.0),
                max_images=config.get("max_images", 8),
                enable_content_analysis=config.get("enable_content_analysis", True),
            )
            logger.info(f"Image filter initialized: {config}")
        except Exception as e:
            logger.debug(
                f"Failed to read image optimization parameters from configuration: {e}, using default parameters"
            )
            _global_image_filter = HybridImageFilter()

    return _global_image_filter
