"""
Screen screenshot capture
Using mss library for efficient screen screenshots
"""

import hashlib
import io
import os
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

import mss
from core.logger import get_logger
from core.models import RawRecord, RecordType
from core.paths import get_tmp_dir
from core.settings import get_settings
from PIL import Image
from processing.image_manager import get_image_manager

from .base import BaseCapture

logger = get_logger(__name__)


class ScreenshotCapture(BaseCapture):
    """Screen screenshot capturer"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event
        # Do not keep a cross-thread MSS instance; create per call/thread
        self.mss_instance: Optional[mss.mss] = None
        self._last_screenshot_time = 0
        # Per-monitor deduplication state
        self._last_hashes: Dict[int, Optional[str]] = {}
        self._last_force_save_times: Dict[int, float] = {}
        self._force_save_interval = 5.0  # Force save interval (seconds)
        self._screenshot_count = 0
        self._compression_quality = 85
        self._max_width = 1920
        self._max_height = 1080
        self._enable_phash = True
        self._not_started_warning_logged = False  # Track if warning has been logged

        # Use unified path tool to get screenshot directory
        self.tmp_dir = str(get_tmp_dir("screenshots"))
        self._ensure_tmp_dir()

        # Get image manager
        self.image_manager = get_image_manager()

    def capture(self) -> RawRecord:
        """Capture screenshots for enabled monitors.

        Reads enabled monitor indices from settings.screenshot.screen_settings and
        captures each enabled monitor in a single pass. Emits a record per monitor
        via callback; returns the last record (for compatibility).
        """
        try:
            enabled_indices = self._get_enabled_monitor_indices()

            last_record: Optional[RawRecord] = None
            with mss.mss() as sct:
                max_idx = len(sct.monitors) - 1
                for idx in enabled_indices:
                    if not isinstance(idx, int) or idx < 1 or idx > max_idx:
                        continue
                    record = self._capture_one_monitor(sct, idx)
                    if record is not None:
                        last_record = record
            return last_record
        except Exception as e:
            logger.error(f"Failed to capture screenshots: {e}")
            return None

    def _get_enabled_monitor_indices(self) -> List[int]:
        """Load enabled monitor indices from settings.

        Returns:
            - If screen settings exist and some are enabled: list of enabled indices
            - If screen settings exist but none enabled: empty list (respect user's choice)
            - If no screen settings configured or read fails: [1] (primary)
        """
        try:
            settings = get_settings()
            screens = settings.get("screenshot.screen_settings", None)
            if not isinstance(screens, list) or len(screens) == 0:
                # Not configured -> default to primary only
                return [1]
            enabled = [int(s.get("monitor_index")) for s in screens if s.get("is_enabled")]
            # Deduplicate while preserving order
            seen = set()
            result: List[int] = []
            for i in enabled:
                if i not in seen:
                    seen.add(i)
                    result.append(i)
            return result
        except Exception as e:
            logger.warning(f"Failed to read screen settings, fallback to primary: {e}")
            return [1]

    def _capture_one_monitor(self, sct: mss.mss, monitor_index: int) -> Optional[RawRecord]:
        """Capture one monitor and emit a record if not duplicate (or force-save interval reached)."""
        try:
            monitor = sct.monitors[monitor_index]
            screenshot = sct.grab(monitor)

            # Convert to PIL
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img = self._process_image(img)

            img_hash = self._calculate_hash(img)
            current_time = time.time()
            last_hash = self._last_hashes.get(monitor_index)
            last_force = self._last_force_save_times.get(monitor_index, 0.0)
            is_duplicate = last_hash == img_hash
            time_since_force_save = current_time - last_force
            should_force_save = time_since_force_save >= self._force_save_interval

            if is_duplicate and not should_force_save:
                logger.debug(f"Skip duplicate screenshot on monitor {monitor_index}")
                return None

            if is_duplicate and should_force_save:
                logger.debug(
                    f"Force keep duplicate screenshot on monitor {monitor_index} "
                    f"({time_since_force_save:.1f}s since last save)"
                )
                self._last_force_save_times[monitor_index] = current_time

            self._last_hashes[monitor_index] = img_hash
            self._screenshot_count += 1

            # Convert to bytes and process
            img_bytes = self._image_to_bytes(img)
            self.image_manager.process_image_for_cache(img_hash, img_bytes)
            screenshot_path = self._generate_screenshot_path(img_hash)

            screenshot_data = {
                "action": "capture",
                "width": img.width,
                "height": img.height,
                "format": "JPEG",
                "hash": img_hash,
                "monitor": monitor,
                "monitor_index": monitor_index,
                "timestamp": datetime.now().isoformat(),
                "screenshotPath": screenshot_path,
            }

            record = RawRecord(
                timestamp=datetime.now(),
                type=RecordType.SCREENSHOT_RECORD,
                data=screenshot_data,
                screenshot_path=screenshot_path,
            )

            logger.debug(
                f"Screenshot added to memory cache: {img_hash[:8]} (monitor {monitor_index})"
            )

            if self.on_event:
                self.on_event(record)

            return record
        except Exception as e:
            logger.error(f"Failed to capture monitor {monitor_index}: {e}")
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
        self._not_started_warning_logged = False  # Reset warning flag when starting
        try:
            # Lazily create MSS instances per capture call; nothing to init here
            logger.info("Screen screenshot capture started")
        except Exception as e:
            logger.error(f"Failed to start screen screenshot capture: {e}")
            self.is_running = False

    def stop(self):
        """Stop screen screenshot capture"""
        if not self.is_running:
            return

        self.is_running = False
        # No persistent MSS instance to close; each capture manages its own
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
            # Only log warning once when not started (avoid spamming logs during sleep/idle)
            if not self._not_started_warning_logged:
                logger.warning("Screen screenshot capture not started")
                self._not_started_warning_logged = True
            return

        current_time = time.time()
        if current_time - self._last_screenshot_time >= interval:
            self.capture()
            self._last_screenshot_time = current_time

    def get_monitor_info(self) -> dict:
        """Get monitor information"""
        try:
            # Use a fresh MSS instance to query monitors in the current thread
            with mss.mss() as sct:
                monitors = sct.monitors
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
            "last_hashes": self._last_hashes,
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
