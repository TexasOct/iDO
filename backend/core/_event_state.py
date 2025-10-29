"""
共享事件发射状态，确保不同导入路径（core.events / rewind_backend.core.events）使用同一份数据。
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class EventState:
    app_handle: Optional[Any] = None


event_state = EventState()
