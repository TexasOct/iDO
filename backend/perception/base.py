"""
感知层基础抽象类
定义 BaseCapture 抽象类
"""

from abc import ABC, abstractmethod
from typing import Any
from core.models import RawRecord


class BaseCapture(ABC):
    """基础捕获抽象类"""
    
    def __init__(self):
        self.is_running = False
    
    @abstractmethod
    def capture(self) -> RawRecord:
        """捕获原始数据"""
        pass
    
    @abstractmethod
    def output(self) -> None:
        """输出处理后的数据"""
        pass
    
    def start(self):
        """开始捕获"""
        self.is_running = True
        # TODO: 实现启动逻辑
    
    def stop(self):
        """停止捕获"""
        self.is_running = False
        # TODO: 实现停止逻辑
