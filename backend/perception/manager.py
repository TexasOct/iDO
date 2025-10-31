"""
异步任务管理器
负责协调键盘、鼠标、屏幕截图的异步采集

使用工厂模式创建平台特定的监控器
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from core.logger import get_logger
from .factory import create_keyboard_monitor, create_mouse_monitor
from .screenshot_capture import ScreenshotCapture
from .storage import SlidingWindowStorage, EventBuffer
from .screen_state_monitor import create_screen_state_monitor
from core.models import RawRecord

logger = get_logger(__name__)


class PerceptionManager:
    """感知层管理器"""

    def __init__(self,
                 capture_interval: float = 1.0,
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

        # 使用工厂模式创建平台特定的监控器
        self.keyboard_capture = create_keyboard_monitor(self._on_keyboard_event)
        self.mouse_capture = create_mouse_monitor(self._on_mouse_event)
        self.screenshot_capture = ScreenshotCapture(self._on_screenshot_event)

        # 初始化存储
        self.storage = SlidingWindowStorage(window_size)
        self.event_buffer = EventBuffer()

        # 运行状态
        self.is_running = False
        self.is_paused = False  # 暂停状态（熄屏时）
        self.tasks: Dict[str, asyncio.Task] = {}

        # 屏幕状态监听器
        self.screen_state_monitor = create_screen_state_monitor(
            on_screen_lock=self._on_screen_lock,
            on_screen_unlock=self._on_screen_unlock
        )

    def _on_screen_lock(self) -> None:
        """屏幕锁定/系统睡眠回调"""
        if not self.is_running:
            return

        logger.info("屏幕已锁定/系统睡眠，暂停感知")
        self.is_paused = True

        # 暂停各个捕获器
        try:
            self.keyboard_capture.stop()
            self.mouse_capture.stop()
            self.screenshot_capture.stop()
            logger.debug("所有捕获器已暂停")
        except Exception as e:
            logger.error(f"暂停捕获器失败: {e}")

    def _on_screen_unlock(self) -> None:
        """屏幕解锁/系统唤醒回调"""
        if not self.is_running or not self.is_paused:
            return

        logger.info("屏幕已解锁/系统唤醒，恢复感知")
        self.is_paused = False

        # 恢复各个捕获器
        try:
            self.keyboard_capture.start()
            self.mouse_capture.start()
            self.screenshot_capture.start()
            logger.debug("所有捕获器已恢复")
        except Exception as e:
            logger.error(f"恢复捕获器失败: {e}")

    def _on_keyboard_event(self, record: RawRecord) -> None:
        """键盘事件回调"""
        # 暂停时不处理事件
        if self.is_paused:
            return

        try:
            # 记录所有键盘事件，供后续处理保留使用情况上下文
            self.storage.add_record(record)
            self.event_buffer.add(record)

            if self.on_data_captured:
                self.on_data_captured(record)

            logger.debug(f"键盘事件已记录: {record.data.get('key', 'unknown')}")
        except Exception as e:
            logger.error(f"处理键盘事件失败: {e}")

    def _on_mouse_event(self, record: RawRecord) -> None:
        """鼠标事件回调"""
        # 暂停时不处理事件
        if self.is_paused:
            return

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
        # 暂停时不处理事件
        if self.is_paused:
            return

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
        from datetime import datetime

        if self.is_running:
            logger.warning("感知管理器已在运行中")
            return

        try:
            start_total = datetime.now()
            self.is_running = True
            self.is_paused = False

            # 启动屏幕状态监听器
            start_time = datetime.now()
            self.screen_state_monitor.start()
            logger.debug(f"屏幕状态监听器启动耗时: {(datetime.now() - start_time).total_seconds():.3f}s")

            # 启动各个捕获器
            start_time = datetime.now()
            self.keyboard_capture.start()
            logger.debug(f"键盘捕获启动耗时: {(datetime.now() - start_time).total_seconds():.3f}s")

            start_time = datetime.now()
            self.mouse_capture.start()
            logger.debug(f"鼠标捕获启动耗时: {(datetime.now() - start_time).total_seconds():.3f}s")

            start_time = datetime.now()
            self.screenshot_capture.start()
            logger.debug(f"屏幕截图捕获启动耗时: {(datetime.now() - start_time).total_seconds():.3f}s")

            # 启动异步任务
            start_time = datetime.now()
            self.tasks["screenshot_task"] = asyncio.create_task(self._screenshot_loop())
            self.tasks["cleanup_task"] = asyncio.create_task(self._cleanup_loop())
            logger.debug(f"异步任务创建耗时: {(datetime.now() - start_time).total_seconds():.3f}s")

            total_elapsed = (datetime.now() - start_total).total_seconds()
            logger.info(f"感知管理器已启动 (总耗时: {total_elapsed:.3f}s, 屏幕状态监听已启用)")

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
            self.is_paused = False

            # 停止屏幕状态监听器
            self.screen_state_monitor.stop()

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
            loop = asyncio.get_event_loop()
            while self.is_running:
                # 在线程池中执行同步的截图操作，避免阻塞事件循环
                await loop.run_in_executor(
                    None,
                    self.screenshot_capture.capture_with_interval,
                    self.capture_interval
                )
                await asyncio.sleep(0.1)  # 短暂休眠，避免占用过多 CPU
        except asyncio.CancelledError:
            logger.debug("屏幕截图循环任务已取消")
        except Exception as e:
            logger.error(f"屏幕截图循环任务失败: {e}")

    async def _cleanup_loop(self) -> None:
        """清理循环任务"""
        try:
            # 第一次清理延迟 30 秒（给初始化留出时间）
            cleanup_interval = 30
            first_cleanup = True

            while self.is_running:
                await asyncio.sleep(cleanup_interval)

                if not self.is_running:
                    break

                # 第一次清理后，改为每 60 秒清理一次
                if first_cleanup:
                    first_cleanup = False
                    cleanup_interval = 60

                try:
                    self.storage._cleanup_expired_records()
                    logger.debug("执行定期清理")
                except Exception as e:
                    logger.error(f"清理过期记录失败: {e}")
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

    def get_records_in_last_n_seconds(self, seconds: int) -> list:
        """获取最近 N 秒内的记录"""
        from datetime import datetime, timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=seconds)
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
        self.capture_interval = max(1, interval)  # 最小间隔 0.1 秒
        logger.info(f"捕获间隔已设置为: {self.capture_interval} 秒")

    def set_compression_settings(self, quality: int = 85, max_width: int = 1920, max_height: int = 1080) -> None:
        """设置屏幕截图压缩参数"""
        self.screenshot_capture.set_compression_settings(quality, max_width, max_height)
