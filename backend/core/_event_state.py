"""
Shared event emission state, ensuring different import paths (core.events / ido_backend.core.events) use the same data.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class EventState:
    app_handle: Optional[Any] = None


event_state = EventState()
