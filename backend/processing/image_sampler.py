"""
Image sampling logic
Controls which images to send to LLM based on time intervals and quantity limits
"""

from typing import List

from core.logger import get_logger
from core.models import RawRecord, RecordType

logger = get_logger(__name__)


class ImageSampler:
    """
    Smart image sampler - selects representative images from a sequence

    Responsibilities:
    - Time-based sampling (minimum interval between samples)
    - Quantity-based limiting (maximum images per batch)
    - Always includes first and last images
    """

    def __init__(self, min_interval: float = 2.5, max_images: int = 8):
        """
        Initialize sampler

        Args:
            min_interval: Minimum seconds between sampled images (default 2.5)
            max_images: Maximum images to include (default 8)
        """
        self.min_interval = min_interval
        self.max_images = max_images

        logger.debug(
            f"ImageSampler initialized: min_interval={min_interval}s, max_images={max_images}"
        )

    def sample(self, records: List[RawRecord]) -> List[RawRecord]:
        """
        Sample images from record list

        Strategy:
        1. Always include first image
        2. Sample middle images by time interval
        3. Always include last image if different from first
        4. Enforce max_images limit

        Args:
            records: List of records (should be screenshots)

        Returns:
            Sampled subset of records
        """
        # Filter to only screenshots
        screenshots = [r for r in records if r.type == RecordType.SCREENSHOT_RECORD]

        if not screenshots:
            return []

        # If within limit, return all
        if len(screenshots) <= self.max_images:
            logger.debug(f"All {len(screenshots)} images within limit, no sampling needed")
            return screenshots

        sampled = []

        # Always include first
        sampled.append(screenshots[0])
        last_time = screenshots[0].timestamp.timestamp()

        # Sample middle images by time interval
        for screenshot in screenshots[1:-1]:
            current_time = screenshot.timestamp.timestamp()

            # Check if enough time has passed
            if current_time - last_time >= self.min_interval:
                sampled.append(screenshot)
                last_time = current_time

                # Check if we've hit the limit (save one slot for last image)
                if len(sampled) >= self.max_images - 1:
                    break

        # Always include last if we have room and it's different from first
        if len(screenshots) > 1 and len(sampled) < self.max_images:
            last_screenshot = screenshots[-1]
            if last_screenshot.timestamp != screenshots[0].timestamp:
                sampled.append(last_screenshot)

        logger.debug(
            f"Sampled {len(sampled)}/{len(screenshots)} images "
            f"(interval: {self.min_interval}s, max: {self.max_images})"
        )

        return sampled
