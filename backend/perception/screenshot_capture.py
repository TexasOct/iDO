"""
Screen screenshot capture
Using mss library for efficient screen screenshots
"""

import time
import hashlib
import os
from datetime import datetime
from typing import Optional, Callable
import mss
from PIL import Image
import io
from core.models import RawRecord, RecordType
from core.logger import get_logger
from core.paths import get_tmp_dir
from processing.image_manager import get_image_manager
from .base import BaseCapture

logger = get_logger(__name__)


class ScreenshotCapture(BaseCapture):
    """Screen screenshot capturer"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event
        self.mss_instance: Optional[mss.mss] = None
        self._last_screenshot_time = 0
        self._last_hash = None
        self._last_force_save_time = 0  # Last force save time
        self._force_save_interval = 5.0  # Force save interval (seconds)
        self._screenshot_count = 0
        self._compression_quality = 85
        self._max_width = 1920
        self._max_height = 1080
        self._enable_phash = True

        # Use unified path tool to get screenshot directory
        self.tmp_dir = str(get_tmp_dir("screenshots"))
        self._ensure_tmp_dir()

        # Get image manager
        self.image_manager = get_image_manager()

    def capture(self) -> RawRecord:
        """Capture screen screenshot"""
        try:
            if not self.mss_instance:
                self.mss_instance = mss.mss()

            # Get primary monitor
            monitor = self.mss_instance.monitors[
                1
            ]  # 0 is all monitors, 1 is primary monitor

            # Capture screen
            screenshot = self.mss_instance.grab(monitor)

            # Convert to PIL Image
            img = Image.frombytes(
                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
            )

            # Compress and resize
            img = self._process_image(img)

            # Calculate hash value (for deduplication)
            img_hash = self._calculate_hash(img)

            # Check if same as previous screenshot
            current_time = time.time()
            is_duplicate = self._last_hash == img_hash
            time_since_force_save = current_time - self._last_force_save_time
            should_force_save = time_since_force_save >= self._force_save_interval

            if is_duplicate and not should_force_save:
                logger.debug("Skip duplicate screenshot")
                return None

            if is_duplicate and should_force_save:
                logger.debug(
                    f"Force keep duplicate screenshot ({time_since_force_save:.1f}s since last save)"
                )
                self._last_force_save_time = current_time

            self._last_hash = img_hash
            self._screenshot_count += 1

            # Convert to byte data
            img_bytes = self._image_to_bytes(img)

            # Process image: create thumbnail, save to disk, and add to memory cache
            # This ensures persistence even after application restart
            self.image_manager.process_image_for_cache(img_hash, img_bytes)

            # Generate virtual path (actual save happens during Activity persistence)
            screenshot_path = self._generate_screenshot_path(img_hash)

            screenshot_data = {
                "action": "capture",
                "width": img.width,
                "height": img.height,
                "format": "JPEG",
                # img_data not saved in metadata, retrieved from cache via hash
                "hash": img_hash,
                "monitor": monitor,
                "timestamp": datetime.now().isoformat(),
                "screenshotPath": screenshot_path,  # Virtual path
            }

            record = RawRecord(
                timestamp=datetime.now(),
                type=RecordType.SCREENSHOT_RECORD,
                data=screenshot_data,
                screenshot_path=screenshot_path,
            )

            # Don't store image_data, completely rely on memory cache
            logger.debug(f"Screenshot added to memory cache: {img_hash[:8]}")

            if self.on_event:
                self.on_event(record)

            return record

        except Exception as e:
            logger.error(f"Failed to clean up expired records: {e}")
            return None

    def output(self) -> None:
        """Output processed data (screen screenshots don't need buffering)"""
        pass

    def start(self):
        """Start screen screenshot capture"""
        if self.is_running:
            logger.warning("Screen screenshot capture is already running")
            return

        self.is_running = True
        try:
            self.mss_instance = mss.mss()
            logger.info("Screen screenshot capture started")
        except Exception as e:
            logger.error(f"Failed to start screen screenshot capture: {e}")
            self.is_running = False

    def stop(self):
        """Stop screen screenshot capture"""
        if not self.is_running:
            return

        self.is_running = False
        if self.mss_instance:
            self.mss_instance.close()
            self.mss_instance = None
        logger.info("Screen screenshot capture stopped")

    def _process_image(self, img: Image.Image) -> Image.Image:
        """Process image: resize and compress"""
        try:
            # Resize (maintain aspect ratio)
            if img.width > self._max_width or img.height > self._max_height:
                img.thumbnail(
                    (self._max_width, self._max_height), Image.Resampling.LANCZOS
                )

            # Convert to RGB (if needed)
            if img.mode != "RGB":
                img = img.convert("RGB")

            return img

        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return img

    def _calculate_hash(self, img: Image.Image) -> str:
        """Calculate image hash value"""
        try:
            if self._enable_phash:
                # Use perceptual hash (pHash)
                return self._calculate_phash(img)
            else:
                # Use MD5 hash
                img_bytes = self._image_to_bytes(img)
                return hashlib.md5(img_bytes).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate image hash: {e}")
            return ""

    def _calculate_phash(self, img: Image.Image) -> str:
        """Calculate perceptual hash (simplified version)"""
        try:
            # Simplified perceptual hash implementation
            # Scale image to 8x8
            img_small = img.resize((8, 8), Image.Resampling.LANCZOS)
            img_gray = img_small.convert("L")

            # Calculate average pixel value
            pixels = list(img_gray.getdata())
            avg = sum(pixels) / len(pixels)

            # Generate hash
            hash_bits = []
            for pixel in pixels:
                hash_bits.append("1" if pixel > avg else "0")

            # Convert to hexadecimal
            hash_str = "".join(hash_bits)
            return hex(int(hash_str, 2))[2:].zfill(16)

        except Exception as e:
            logger.error(f"Failed to calculate perceptual hash: {e}")
            return ""

    def _image_to_bytes(self, img: Image.Image) -> bytes:
        """Convert image to byte data"""
        try:
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG", quality=self._compression_quality)
            return img_bytes.getvalue()
        except Exception as e:
            logger.error(f"Failed to convert image to bytes: {e}")
            return b""

    def capture_with_interval(self, interval: float = 1.0):
        """Capture screen screenshots at specified interval"""
        if not self.is_running:
            logger.warning("Screen screenshot capture not started")
            return

        current_time = time.time()
        if current_time - self._last_screenshot_time >= interval:
            self.capture()
            self._last_screenshot_time = current_time

    def get_monitor_info(self) -> dict:
        """Get monitor information"""
        try:
            if not self.mss_instance:
                self.mss_instance = mss.mss()

            monitors = self.mss_instance.monitors
            return {
                "monitor_count": len(monitors) - 1,  # Exclude "All in One" monitor
                "monitors": monitors[1:],  # Exclude "All in One"
                "primary_monitor": monitors[1] if len(monitors) > 1 else None,
            }
        except Exception as e:
            logger.error(f"Failed to get monitor information: {e}")
            return {"monitor_count": 0, "monitors": [], "primary_monitor": None}

    def set_compression_settings(
        self, quality: int = 85, max_width: int = 1920, max_height: int = 1080
    ) -> None:
        """Set compression parameters"""
        self._compression_quality = max(1, min(100, quality))
        self._max_width = max(100, max_width)
        self._max_height = max(100, max_height)
        logger.info(
            f"Compression settings updated: quality={self._compression_quality}, max_size=({self._max_width}, {self._max_height})"
        )

    def get_stats(self) -> dict:
        """Get capture statistics"""
        return {
            "is_running": self.is_running,
            "screenshot_count": self._screenshot_count,
            "last_screenshot_time": self._last_screenshot_time,
            "last_hash": self._last_hash,
            "compression_quality": self._compression_quality,
            "max_size": (self._max_width, self._max_height),
            "enable_phash": self._enable_phash,
            "tmp_dir": self.tmp_dir,
        }

    def _ensure_tmp_dir(self) -> None:
        """Ensure tmp directory exists"""
        try:
            os.makedirs(self.tmp_dir, exist_ok=True)
            logger.debug(f"Screenshot temporary directory created: {self.tmp_dir}")
        except Exception as e:
            logger.error(f"Failed to create screenshot temporary directory: {e}")

    def _generate_screenshot_path(self, img_hash: str) -> str:
        """Generate virtual path for screenshot (actual save handled by ImageManager during persistence)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"screenshot_{timestamp}_{img_hash[:8]}.jpg"
            # Return virtual path, actual file not yet created
            return os.path.join(self.tmp_dir, filename)
        except Exception as e:
            logger.error(f"Failed to generate screenshot path: {e}")
            return os.path.join(self.tmp_dir, f"screenshot_{img_hash[:8]}.jpg")

    def _save_screenshot_to_file(self, img_bytes: bytes, img_hash: str) -> str:
        """Save screenshot to file and return file path (deprecated, only for compatibility)"""
        logger.warning(
            "_save_screenshot_to_file is deprecated, use ImageManager.persist_image instead"
        )
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"screenshot_{timestamp}_{img_hash[:8]}.jpg"
            file_path = os.path.join(self.tmp_dir, filename)

            with open(file_path, "wb") as f:
                f.write(img_bytes)

            logger.debug(f"Screenshot saved to: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save screenshot to file: {e}")
            return ""

    def cleanup_old_screenshots(self, max_age_hours: int = 24) -> int:
        """Clean up old screenshot files

        Args:
            max_age_hours: Maximum age in hours for screenshot files

        Returns:
            Number of files cleaned up
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0

            for filename in os.listdir(self.tmp_dir):
                if filename.startswith("screenshot_") and filename.endswith(".jpg"):
                    file_path = os.path.join(self.tmp_dir, filename)
                    file_age = current_time - os.path.getmtime(file_path)

                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.debug(f"Deleted old screenshot: {filename}")

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old screenshot files")

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to clean up old screenshots: {e}")
            return 0
