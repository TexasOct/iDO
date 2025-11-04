"""
Perception layer base abstract classes
Define BaseCapture interface and specific monitor interfaces
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Callable, Dict
from core.models import RawRecord


class BaseCapture(ABC):
    """Base capture abstract class"""

    def __init__(self):
        self.is_running = False

    @abstractmethod
    def capture(self) -> RawRecord:
        """Capture raw data (synchronous method, for testing)"""
        pass

    @abstractmethod
    def output(self) -> None:
        """Output processed data"""
        pass

    @abstractmethod
    def start(self):
        """Start capturing"""
        pass

    @abstractmethod
    def stop(self):
        """Stop capturing"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        pass


class BaseKeyboardMonitor(BaseCapture):
    """Keyboard monitor base class"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event

    @abstractmethod
    def is_special_key(self, key_data: dict) -> bool:
        """Determine if this is a special key (needs to be recorded)

        Args:
            key_data: Key data dictionary

        Returns:
            bool: Whether this is a special key
        """
        pass


class BaseMouseMonitor(BaseCapture):
    """Mouse monitor base class"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event

    @abstractmethod
    def is_important_event(self, event_data: dict) -> bool:
        """Determine if this is an important event (needs to be recorded)

        Args:
            event_data: Event data dictionary

        Returns:
            bool: Whether this is an important event
        """
        pass
