"""
屏幕状态监听器
监听屏幕锁定/解锁、睡眠/唤醒事件，用于自动暂停/恢复感知
"""

import platform
import threading
from typing import Callable, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class ScreenStateMonitor:
    """屏幕状态监听器基类"""

    def __init__(self, on_screen_lock: Optional[Callable] = None, on_screen_unlock: Optional[Callable] = None):
        """
        初始化屏幕状态监听器

        Args:
            on_screen_lock: 屏幕锁定/睡眠回调
            on_screen_unlock: 屏幕解锁/唤醒回调
        """
        self.on_screen_lock = on_screen_lock
        self.on_screen_unlock = on_screen_unlock
        self.is_running = False
        self._thread = None

    def start(self) -> None:
        """启动监听"""
        raise NotImplementedError

    def stop(self) -> None:
        """停止监听"""
        raise NotImplementedError


class MacOSScreenStateMonitor(ScreenStateMonitor):
    """macOS 屏幕状态监听器"""

    def start(self) -> None:
        """启动监听"""
        if self.is_running:
            return

        try:
            from AppKit import NSWorkspace
            from Foundation import NSNotificationCenter

            self.is_running = True

            # 获取通知中心
            nc = NSWorkspace.sharedWorkspace().notificationCenter()

            # 监听屏幕锁定
            nc.addObserver_selector_name_object_(
                self, 'screenDidLock:', 'NSWorkspaceScreensDidSleepNotification', None
            )

            # 监听屏幕唤醒
            nc.addObserver_selector_name_object_(
                self, 'screenDidUnlock:', 'NSWorkspaceScreensDidWakeNotification', None
            )

            # 监听系统睡眠
            nc.addObserver_selector_name_object_(
                self, 'screenDidLock:', 'NSWorkspaceWillSleepNotification', None
            )

            # 监听系统唤醒
            nc.addObserver_selector_name_object_(
                self, 'screenDidUnlock:', 'NSWorkspaceDidWakeNotification', None
            )

            logger.info("macOS 屏幕状态监听器已启动")

        except ImportError:
            logger.error("无法导入 AppKit/Foundation，屏幕状态监听不可用")
            self.is_running = False
        except Exception as e:
            logger.error(f"启动 macOS 屏幕状态监听器失败: {e}")
            self.is_running = False

    def screenDidLock_(self, notification) -> None:
        """屏幕锁定/睡眠回调"""
        logger.info("检测到屏幕锁定/系统睡眠")
        if self.on_screen_lock:
            try:
                self.on_screen_lock()
            except Exception as e:
                logger.error(f"执行屏幕锁定回调失败: {e}")

    def screenDidUnlock_(self, notification) -> None:
        """屏幕解锁/唤醒回调"""
        logger.info("检测到屏幕解锁/系统唤醒")
        if self.on_screen_unlock:
            try:
                self.on_screen_unlock()
            except Exception as e:
                logger.error(f"执行屏幕解锁回调失败: {e}")

    def stop(self) -> None:
        """停止监听"""
        if not self.is_running:
            return

        try:
            from AppKit import NSWorkspace

            self.is_running = False

            # 移除所有观察者
            nc = NSWorkspace.sharedWorkspace().notificationCenter()
            nc.removeObserver_(self)

            logger.info("macOS 屏幕状态监听器已停止")

        except Exception as e:
            logger.error(f"停止 macOS 屏幕状态监听器失败: {e}")


class WindowsScreenStateMonitor(ScreenStateMonitor):
    """Windows 屏幕状态监听器"""

    def start(self) -> None:
        """启动监听"""
        if self.is_running:
            return

        try:
            import win32api
            import win32con
            import win32gui

            self.is_running = True

            # 在后台线程中监听 Windows 消息
            self._thread = threading.Thread(target=self._message_loop, daemon=True)
            self._thread.start()

            logger.info("Windows 屏幕状态监听器已启动")

        except ImportError:
            logger.error("无法导入 pywin32，屏幕状态监听不可用")
            self.is_running = False
        except Exception as e:
            logger.error(f"启动 Windows 屏幕状态监听器失败: {e}")
            self.is_running = False

    def _message_loop(self) -> None:
        """Windows 消息循环"""
        try:
            import win32api
            import win32con
            import win32gui

            # 创建隐藏窗口用于接收消息
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = self._wnd_proc
            wc.lpszClassName = "RewindScreenStateMonitor"
            wc.hInstance = win32api.GetModuleHandle(None)

            class_atom = win32gui.RegisterClass(wc)
            hwnd = win32gui.CreateWindow(
                class_atom, "Rewind Screen State Monitor",
                0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
            )

            # 消息循环
            while self.is_running:
                win32gui.PumpWaitingMessages()
                threading.Event().wait(0.1)

            win32gui.DestroyWindow(hwnd)
            win32gui.UnregisterClass(class_atom, wc.hInstance)

        except Exception as e:
            logger.error(f"Windows 消息循环异常: {e}")

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        """Windows 窗口消息处理"""
        import win32con

        if msg == win32con.WM_POWERBROADCAST:
            if wparam == win32con.PBT_APMSUSPEND:
                # 系统挂起
                logger.info("检测到系统挂起")
                if self.on_screen_lock:
                    self.on_screen_lock()
            elif wparam == win32con.PBT_APMRESUMEAUTOMATIC:
                # 系统恢复
                logger.info("检测到系统恢复")
                if self.on_screen_unlock:
                    self.on_screen_unlock()

        return 0

    def stop(self) -> None:
        """停止监听"""
        if not self.is_running:
            return

        self.is_running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info("Windows 屏幕状态监听器已停止")


class LinuxScreenStateMonitor(ScreenStateMonitor):
    """Linux 屏幕状态监听器"""

    def start(self) -> None:
        """启动监听"""
        if self.is_running:
            return

        try:
            # 尝试使用 dbus 监听 logind 信号
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop

            DBusGMainLoop(set_as_default=True)

            self.is_running = True

            # 在后台线程中运行 DBus 主循环
            self._thread = threading.Thread(target=self._dbus_loop, daemon=True)
            self._thread.start()

            logger.info("Linux 屏幕状态监听器已启动")

        except ImportError:
            logger.warning("无法导入 dbus，屏幕状态监听不可用（需要安装 python-dbus）")
            self.is_running = False
        except Exception as e:
            logger.error(f"启动 Linux 屏幕状态监听器失败: {e}")
            self.is_running = False

    def _dbus_loop(self) -> None:
        """DBus 主循环"""
        try:
            import dbus
            from gi.repository import GLib

            bus = dbus.SystemBus()

            # 监听 PrepareForSleep 信号
            bus.add_signal_receiver(
                self._handle_prepare_for_sleep,
                'PrepareForSleep',
                'org.freedesktop.login1.Manager',
                'org.freedesktop.login1'
            )

            # 运行主循环
            loop = GLib.MainLoop()
            while self.is_running:
                loop.get_context().iteration(False)
                threading.Event().wait(0.1)

        except Exception as e:
            logger.error(f"Linux DBus 循环异常: {e}")

    def _handle_prepare_for_sleep(self, sleep: bool) -> None:
        """处理系统睡眠/唤醒信号"""
        if sleep:
            logger.info("检测到系统即将睡眠")
            if self.on_screen_lock:
                self.on_screen_lock()
        else:
            logger.info("检测到系统唤醒")
            if self.on_screen_unlock:
                self.on_screen_unlock()

    def stop(self) -> None:
        """停止监听"""
        if not self.is_running:
            return

        self.is_running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info("Linux 屏幕状态监听器已停止")


def create_screen_state_monitor(
    on_screen_lock: Optional[Callable] = None,
    on_screen_unlock: Optional[Callable] = None
) -> ScreenStateMonitor:
    """
    创建适合当前平台的屏幕状态监听器

    Args:
        on_screen_lock: 屏幕锁定/睡眠回调
        on_screen_unlock: 屏幕解锁/唤醒回调

    Returns:
        屏幕状态监听器实例
    """
    system = platform.system()

    if system == "Darwin":
        return MacOSScreenStateMonitor(on_screen_lock, on_screen_unlock)
    elif system == "Windows":
        return WindowsScreenStateMonitor(on_screen_lock, on_screen_unlock)
    elif system == "Linux":
        return LinuxScreenStateMonitor(on_screen_lock, on_screen_unlock)
    else:
        logger.warning(f"不支持的平台: {system}，屏幕状态监听不可用")
        return ScreenStateMonitor(on_screen_lock, on_screen_unlock)
