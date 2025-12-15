"""
Image processing module

Provides unified image processing capabilities:
- Image compression (resolution-based)
- Duplicate detection (perceptual hash)
- Content analysis (contrast, edge detection, complexity)
- Smart sampling (time/quantity limits)
"""

from .analysis import ImageAnalyzer
from .processing import (
    ImageCompressor,
    ImageDuplicateDetector,
    ImageProcessor,
    ImageSampler,
    get_image_compressor,
    get_image_processor,
)

__all__ = [
    # Classes
    "ImageAnalyzer",
    "ImageCompressor",
    "ImageDuplicateDetector",
    "ImageProcessor",
    "ImageSampler",
    # Factory functions
    "get_image_compressor",
    "get_image_processor",
]
