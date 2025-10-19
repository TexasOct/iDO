"""
异步任务管理器
负责协调键盘、鼠标、屏幕截图的异步采集
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from core.logger import get_logger
from .keyboard_capture import KeyboardCapture
from .mouse_capture import MouseCapture
from .screenshot_capture import ScreenshotCapture
from .storage import SlidingWindowStorage, EventBuffer
from core.models import RawRecord

logger = get_logger(__name__)


class PerceptionManager:
    """感知层管理器"""
    
    def __init__(self, 
                 capture_interval: float = 0.2,
                 window_size: int = 20,
                 on_data_captured: Optional[Callable[[RawRecord], None]] = None):
        """
        初始化感知管理器
        
        Args:
            capture_interval: 屏幕截图捕获间隔（秒）
            window_size: 滑动窗口大小（秒）
            on_data_captured: 数据捕获回调函数
        """
        self.capture_interval = capture_interval
        self.window_size = window_size
        self.on_data_captured = on_data_captured
        
        # 初始化各个捕获器
        self.keyboard_capture = KeyboardCapture(self._on_keyboard_event)
        self.mouse_capture = MouseCapture(self._on_mouse_event)
        self.screenshot_capture = ScreenshotCapture(self._on_screenshot_event)
        
        # 初始化存储
        self.storage = SlidingWindowStorage(window_size)
        self.event_buffer = EventBuffer()
        
        # 运行状态
        self.is_running = False
        self.tasks: Dict[str, asyncio.Task] = {}
        
    def _on_keyboard_event(self, record: RawRecord) -> None:
        """键盘事件回调"""
        try:
            # 只记录特殊键盘事件
            if self.keyboard_capture.is_special_key(record.data):
                self.storage.add_record(record)
                self.event_buffer.add(record)
                
                if self.on_data_captured:
                    self.on_data_captured(record)
                
                logger.debug(f"键盘事件已记录: {record.data.get('key', 'unknown')}")
        except Exception as e:
            logger.error(f"处理键盘事件失败: {e}")
    
    def _on_mouse_event(self, record: RawRecord) -> None:
        """鼠标事件回调"""
        try:
            # 只记录重要鼠标事件
            if self.mouse_capture.is_important_event(record.data):
                self.storage.add_record(record)
                self.event_buffer.add(record)
                
                if self.on_data_captured:
                    self.on_data_captured(record)
                
                logger.debug(f"鼠标事件已记录: {record.data.get('action', 'unknown')}")
        except Exception as e:
            logger.error(f"处理鼠标事件失败: {e}")
    
    def _on_screenshot_event(self, record: RawRecord) -> None:
        """屏幕截图事件回调"""
        try:
            if record:  # 屏幕截图可能为 None（重复截图）
                self.storage.add_record(record)
                self.event_buffer.add(record)
                
                if self.on_data_captured:
                    self.on_data_captured(record)
                
                logger.debug(f"屏幕截图已记录: {record.data.get('width', 0)}x{record.data.get('height', 0)}")
        except Exception as e:
            logger.error(f"处理屏幕截图事件失败: {e}")
    
    async def start(self) -> None:
        """启动感知管理器"""
        if self.is_running:
            logger.warning("感知管理器已在运行中")
            return
        
        try:
            self.is_running = True
            
            # 启动各个捕获器
            self.keyboard_capture.start()
            self.mouse_capture.start()
            self.screenshot_capture.start()
            
            # 启动异步任务
            self.tasks["screenshot_task"] = asyncio.create_task(self._screenshot_loop())
            self.tasks["cleanup_task"] = asyncio.create_task(self._cleanup_loop())
            
            logger.info("感知管理器已启动")
            
        except Exception as e:
            logger.error(f"启动感知管理器失败: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """停止感知管理器"""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            # 停止各个捕获器
            self.keyboard_capture.stop()
            self.mouse_capture.stop()
            self.screenshot_capture.stop()
            
            # 取消异步任务
            for task_name, task in self.tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.tasks.clear()
            
            logger.info("感知管理器已停止")
            
        except Exception as e:
            logger.error(f"停止感知管理器失败: {e}")
    
    async def _screenshot_loop(self) -> None:
        """屏幕截图循环任务"""
        try:
            while self.is_running:
                self.screenshot_capture.capture_with_interval(self.capture_interval)
                await asyncio.sleep(0.1)  # 短暂休眠，避免占用过多 CPU
        except asyncio.CancelledError:
            logger.debug("屏幕截图循环任务已取消")
        except Exception as e:
            logger.error(f"屏幕截图循环任务失败: {e}")
    
    async def _cleanup_loop(self) -> None:
        """清理循环任务"""
        try:
            while self.is_running:
                # 每30秒清理一次过期数据
                await asyncio.sleep(30)
                self.storage._cleanup_expired_records()
                logger.debug("执行定期清理")
        except asyncio.CancelledError:
            logger.debug("清理循环任务已取消")
        except Exception as e:
            logger.error(f"清理循环任务失败: {e}")
    
    def get_recent_records(self, count: int = 100) -> list:
        """获取最近的记录"""
        return self.storage.get_latest_records(count)
    
    def get_records_by_type(self, event_type: str) -> list:
        """根据类型获取记录"""
        from core.models import RecordType
        try:
            event_type_enum = RecordType(event_type)
            return self.storage.get_records_by_type(event_type_enum)
        except ValueError:
            logger.error(f"无效的事件类型: {event_type}")
            return []
    
    def get_records_in_timeframe(self, start_time: datetime, end_time: datetime) -> list:
        """获取指定时间范围内的记录"""
        return self.storage.get_records_in_timeframe(start_time, end_time)
    
    def get_buffered_events(self) -> list:
        """获取缓冲区中的事件"""
        return self.event_buffer.get_all()
    
    def clear_buffer(self) -> None:
        """清空事件缓冲区"""
        self.event_buffer.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        try:
            storage_stats = self.storage.get_stats()
            keyboard_stats = self.keyboard_capture.get_stats()
            mouse_stats = self.mouse_capture.get_stats()
            screenshot_stats = self.screenshot_capture.get_stats()
            
            return {
                "is_running": self.is_running,
                "capture_interval": self.capture_interval,
                "window_size": self.window_size,
                "storage": storage_stats,
                "keyboard": keyboard_stats,
                "mouse": mouse_stats,
                "screenshot": screenshot_stats,
                "buffer_size": self.event_buffer.size(),
                "active_tasks": len([t for t in self.tasks.values() if not t.done()])
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}
    
    def set_capture_interval(self, interval: float) -> None:
        """设置捕获间隔"""
        self.capture_interval = max(0.1, interval)  # 最小间隔 0.1 秒
        logger.info(f"捕获间隔已设置为: {self.capture_interval} 秒")
    
    def set_compression_settings(self, quality: int = 85, max_width: int = 1920, max_height: int = 1080) -> None:
        """设置屏幕截图压缩参数"""
        self.screenshot_capture.set_compression_settings(quality, max_width, max_height)
