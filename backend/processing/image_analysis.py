"""
Unified image analysis module

Provides content-aware image analysis including:
- Contrast detection
- Edge detection
- Complexity analysis
- Motion/activity detection
"""

import io
from typing import Dict, Tuple

import numpy as np
from core.logger import get_logger
from PIL import Image, ImageFilter

logger = get_logger(__name__)


class ImageAnalyzer:
    """
    Unified image analyzer - provides comprehensive image feature analysis

    This class combines functionality previously split between:
    - ImageImportanceAnalyzer (removed)
    - ImageContentAnalyzer (from optimization.py)

    Use cases:
    - Determine if image should be skipped (static/blank content)
    - Adaptive compression quality selection
    - Activity/motion detection
    """

    def __init__(self):
        self.stats = {
            "static_skipped": 0,
            "high_contrast_included": 0,
            "motion_detected": 0,
        }

    def analyze(self, img_bytes: bytes) -> Dict[str, float]:
        """
        Analyze image and return all metrics

        Args:
            img_bytes: Image byte data

        Returns:
            Dictionary with metrics:
            - contrast: Image contrast (0-100)
            - complexity: Color variation complexity (0-100)
            - edge_density: Edge detection density (0-100)
            - edge_activity: Edge activity level (0-100+)
        """
        try:
            img = Image.open(io.BytesIO(img_bytes))

            # Calculate all metrics
            contrast = self._calculate_contrast(img)
            complexity = self._calculate_complexity(img)
            edge_density = self._calculate_edge_density(img)
            edge_activity = self._calculate_edge_activity(img)

            return {
                "contrast": contrast,
                "complexity": complexity,
                "edge_density": edge_density,
                "edge_activity": edge_activity,
            }

        except Exception as e:
            logger.warning(f"Image analysis failed: {e}")
            return {
                "contrast": 0.0,
                "complexity": 0.0,
                "edge_density": 0.0,
                "edge_activity": 0.0,
            }

    def _calculate_contrast(self, img: Image.Image) -> float:
        """
        Calculate image contrast (0-100)

        Uses standard deviation of grayscale pixel values
        """
        gray = img.convert("L")
        pixels = np.array(gray, dtype=np.float32)
        std = float(np.std(pixels))
        # Normalize to 0-100
        return min(100.0, std / 2.55)

    def _calculate_complexity(self, img: Image.Image) -> float:
        """
        Calculate image complexity (0-100) based on color variation

        Higher values indicate more visual detail
        """
        # Resize to small size for fast calculation
        small = img.resize((32, 32), Image.Resampling.LANCZOS)
        pixels = np.array(small, dtype=np.float32)

        # Calculate pixel differences in both directions
        diff_h = np.abs(np.diff(pixels, axis=0)).mean()
        diff_v = np.abs(np.diff(pixels, axis=1)).mean()

        complexity = (diff_h + diff_v) / 2
        # Normalize to 0-100
        return min(100.0, complexity / 2.55)

    def _calculate_edge_density(self, img: Image.Image) -> float:
        """
        Calculate edge density (0-100) using PIL edge detection

        Higher values indicate more edges/structure in image
        """
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_pixels = np.array(edges, dtype=np.float32)

        # Edge pixel ratio
        edge_ratio = (edge_pixels > 50).sum() / edge_pixels.size

        # Normalize to 0-100
        return min(100.0, edge_ratio * 500)

    def _calculate_edge_activity(self, img: Image.Image) -> float:
        """
        Calculate edge activity level (0-100+) using gradient

        Different from edge_density - measures intensity of changes
        """
        gray = img.convert("L")
        pixels = np.array(gray, dtype=np.float32)

        # Calculate mean absolute difference
        if pixels.size > 1:
            edges = np.abs(np.diff(pixels.flatten()))
            return float(np.mean(edges))
        return 0.0

    def is_static_content(self, img_bytes: bytes, threshold: float = 30.0) -> bool:
        """
        Determine if image is static/blank content

        Args:
            img_bytes: Image data
            threshold: Contrast threshold (default 30)

        Returns:
            True if image appears static/blank
        """
        metrics = self.analyze(img_bytes)
        is_static = metrics["contrast"] < threshold

        if is_static:
            self.stats["static_skipped"] += 1

        return is_static

    def has_significant_content(
        self,
        img_bytes: bytes,
        min_contrast: float = 50.0,
        min_activity: float = 10.0
    ) -> Tuple[bool, str]:
        """
        Determine if image has significant content worth processing

        Args:
            img_bytes: Image data
            min_contrast: Minimum contrast threshold
            min_activity: Minimum edge activity threshold

        Returns:
            (should_include, reason)
        """
        metrics = self.analyze(img_bytes)

        # Rule 1: High contrast = potentially meaningful interface change
        if metrics["contrast"] > min_contrast:
            self.stats["high_contrast_included"] += 1
            return True, "High contrast content"

        # Rule 2: Motion detected = user is interacting
        if metrics["edge_activity"] > min_activity:
            self.stats["motion_detected"] += 1
            return True, "Motion detected"

        # Rule 3: Low contrast and no motion = possibly blank/waiting screen
        if metrics["contrast"] < 20:
            self.stats["static_skipped"] += 1
            return False, "Static/blank content"

        return True, "Medium complexity"

    def calculate_importance_score(self, img_bytes: bytes) -> float:
        """
        Calculate overall importance score (0-100)

        Combines multiple metrics into single score for prioritization

        Args:
            img_bytes: Image data

        Returns:
            Importance score (0-100)
        """
        metrics = self.analyze(img_bytes)

        # Weighted combination
        score = (
            metrics["contrast"] * 0.4 +
            metrics["complexity"] * 0.3 +
            metrics["edge_density"] * 0.3
        )

        return min(100.0, max(0.0, score))

    def get_stats(self) -> Dict[str, int]:
        """Get analysis statistics"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            "static_skipped": 0,
            "high_contrast_included": 0,
            "motion_detected": 0,
        }
