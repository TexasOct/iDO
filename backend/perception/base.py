"""
Perception layer base abstract classes
Define monitor interfaces for different types of perception components
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from core.models import RawRecord


class BaseMonitor(ABC):
    """
    Base monitor abstract class - minimal interface for all monitors

    This is the root interface for all perception components.
    """

    def __init__(self):
        self.is_running = False

    @abstractmethod
    def start(self):
        """Start monitoring"""
        pass

    @abstractmethod
    def stop(self):
        """Stop monitoring"""
        pass


class BaseEventListener(BaseMonitor):
    """
    Base event listener abstract class

    For monitors that listen to system events (e.g., screen lock/unlock, system sleep/wake).
    These monitors don't capture data but react to system state changes.
    """
    pass


class BaseCapture(BaseMonitor):
    """
    Base capture abstract class - for data capturing monitors

    For monitors that actively capture data from the system.
    """

    @abstractmethod
    def capture(self) -> Optional[RawRecord]:
        """
        Capture raw data (synchronous method)

        Returns:
            RawRecord if data was captured, None otherwise
        """
        pass

    @abstractmethod
    def output(self) -> None:
        """Output/flush processed data"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get capture statistics

        Returns:
            Dictionary containing statistics about the capture process
        """
        pass


class BaseInputCapture(BaseCapture):
    """
    Base input capture abstract class

    For monitors that capture user input events (keyboard, mouse).
    """

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event


class BaseKeyboardMonitor(BaseInputCapture):
    """
    Keyboard monitor base class

    Captures keyboard input events.
    """

    @abstractmethod
    def is_special_key(self, key_data: dict) -> bool:
        """
        Determine if this is a special key (needs to be recorded)

        Args:
            key_data: Key data dictionary

        Returns:
            bool: Whether this is a special key
        """
        pass


class BaseMouseMonitor(BaseInputCapture):
    """
    Mouse monitor base class

    Captures mouse input events.
    """

    @abstractmethod
    def is_important_event(self, event_data: dict) -> bool:
        """
        Determine if this is an important event (needs to be recorded)

        Args:
            event_data: Event data dictionary

        Returns:
            bool: Whether this is an important event
        """
        pass
