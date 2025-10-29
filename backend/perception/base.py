"""
感知层基础抽象类
定义 BaseCapture 接口和具体监控器的接口
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Callable, Dict
from core.models import RawRecord


class BaseCapture(ABC):
    """基础捕获抽象类"""

    def __init__(self):
        self.is_running = False

    @abstractmethod
    def capture(self) -> RawRecord:
        """捕获原始数据（同步方法，用于测试）"""
        pass

    @abstractmethod
    def output(self) -> None:
        """输出处理后的数据"""
        pass

    @abstractmethod
    def start(self):
        """开始捕获"""
        pass

    @abstractmethod
    def stop(self):
        """停止捕获"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取捕获统计信息"""
        pass


class BaseKeyboardMonitor(BaseCapture):
    """键盘监控器基类"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event

    @abstractmethod
    def is_special_key(self, key_data: dict) -> bool:
        """判断是否为特殊按键（需要记录）

        Args:
            key_data: 按键数据字典

        Returns:
            bool: 是否为特殊按键
        """
        pass


class BaseMouseMonitor(BaseCapture):
    """鼠标监控器基类"""

    def __init__(self, on_event: Optional[Callable[[RawRecord], None]] = None):
        super().__init__()
        self.on_event = on_event

    @abstractmethod
    def is_important_event(self, event_data: dict) -> bool:
        """判断是否为重要事件（需要记录）

        Args:
            event_data: 事件数据字典

        Returns:
            bool: 是否为重要事件
        """
        pass
