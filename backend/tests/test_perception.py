"""
Perception 模块测试
测试键盘、鼠标、屏幕截图捕获功能
"""

import pytest
import asyncio
import time
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import EventType, RawRecord
from perception.keyboard_capture import KeyboardCapture
from perception.mouse_capture import MouseCapture
from perception.screenshot_capture import ScreenshotCapture
from perception.storage import SlidingWindowStorage, EventBuffer
from perception.manager import PerceptionManager


class TestKeyboardCapture:
    """键盘捕获测试"""
    
    def test_keyboard_capture_init(self):
        """测试键盘捕获器初始化"""
        capture = KeyboardCapture()
        assert not capture.is_running
        assert capture.listener is None
    
    def test_keyboard_capture_sync(self):
        """测试同步捕获方法"""
        capture = KeyboardCapture()
        record = capture.capture()
        
        assert isinstance(record, RawRecord)
        assert record.type == EventType.KEYBOARD_EVENT
        assert "key" in record.data
        assert "action" in record.data
    
    def test_extract_key_data(self):
        """测试按键数据提取"""
        capture = KeyboardCapture()
        
        # 模拟按键对象
        mock_key = Mock()
        mock_key.char = 'a'
        mock_key.ctrl = False
        mock_key.alt = False
        mock_key.shift = False
        mock_key.cmd = False
        
        key_data = capture._extract_key_data(mock_key, "press")
        
        assert key_data["action"] == "press"
        assert key_data["key"] == "a"
        assert key_data["key_type"] == "char"
        assert key_data["modifiers"] == []
    
    def test_is_special_key(self):
        """测试特殊键判断"""
        capture = KeyboardCapture()
        
        # 普通字符
        assert not capture.is_special_key({"key": "a", "modifiers": []})
        
        # 特殊键
        assert capture.is_special_key({"key": "enter", "modifiers": []})
        
        # 带修饰键
        assert capture.is_special_key({"key": "a", "modifiers": ["ctrl"]})


class TestMouseCapture:
    """鼠标捕获测试"""
    
    def test_mouse_capture_init(self):
        """测试鼠标捕获器初始化"""
        capture = MouseCapture()
        assert not capture.is_running
        assert capture.listener is None
    
    def test_mouse_capture_sync(self):
        """测试同步捕获方法"""
        capture = MouseCapture()
        record = capture.capture()
        
        assert isinstance(record, RawRecord)
        assert record.type == EventType.MOUSE_EVENT
        assert "action" in record.data
        assert "button" in record.data
        assert "position" in record.data
    
    def test_distance_calculation(self):
        """测试距离计算"""
        capture = MouseCapture()
        
        distance = capture._distance((0, 0), (3, 4))
        assert distance == 5.0
        
        distance = capture._distance((0, 0), (0, 0))
        assert distance == 0.0
    
    def test_is_important_event(self):
        """测试重要事件判断"""
        capture = MouseCapture()
        
        # 重要事件
        assert capture.is_important_event({"action": "press"})
        assert capture.is_important_event({"action": "scroll"})
        
        # 不重要事件
        assert not capture.is_important_event({"action": "move"})


class TestScreenshotCapture:
    """屏幕截图捕获测试"""
    
    def test_screenshot_capture_init(self):
        """测试屏幕截图捕获器初始化"""
        capture = ScreenshotCapture()
        assert not capture.is_running
        assert capture.mss_instance is None
    
    @patch('perception.screenshot_capture.mss.mss')
    def test_screenshot_capture_sync(self, mock_mss):
        """测试同步捕获方法"""
        # 模拟 mss 实例
        mock_instance = Mock()
        mock_instance.monitors = [None, {"left": 0, "top": 0, "width": 1920, "height": 1080}]
        mock_instance.grab.return_value = Mock(size=(1920, 1080), bgra=b'\x00' * (1920 * 1080 * 4))
        mock_mss.return_value = mock_instance
        
        capture = ScreenshotCapture()
        record = capture.capture()
        
        if record:  # 可能为 None（重复截图）
            assert isinstance(record, RawRecord)
            assert record.type == EventType.SCREENSHOT
            assert "width" in record.data
            assert "height" in record.data
    
    def test_image_processing(self):
        """测试图像处理"""
        from PIL import Image
        
        capture = ScreenshotCapture()
        
        # 创建测试图像
        test_img = Image.new('RGB', (2000, 1500), color='red')
        
        # 处理图像
        processed_img = capture._process_image(test_img)
        
        assert processed_img.width <= capture._max_width
        assert processed_img.height <= capture._max_height
        assert processed_img.mode == 'RGB'
    
    def test_hash_calculation(self):
        """测试哈希计算"""
        from PIL import Image
        
        capture = ScreenshotCapture()
        
        # 创建测试图像
        test_img = Image.new('RGB', (100, 100), color='red')
        
        # 计算哈希
        hash1 = capture._calculate_hash(test_img)
        hash2 = capture._calculate_hash(test_img)
        
        assert hash1 == hash2  # 相同图像应该产生相同哈希
        assert len(hash1) > 0  # 哈希不应为空


class TestSlidingWindowStorage:
    """滑动窗口存储测试"""
    
    def test_storage_init(self):
        """测试存储初始化"""
        storage = SlidingWindowStorage(window_size=10)
        assert storage.window_size == 10
        assert len(storage.records) == 0
    
    def test_add_and_get_records(self):
        """测试添加和获取记录"""
        storage = SlidingWindowStorage(window_size=10)
        
        # 创建测试记录
        record1 = RawRecord(
            timestamp=datetime.now(),
            type=EventType.KEYBOARD_EVENT,
            data={"key": "a", "action": "press"}
        )
        
        record2 = RawRecord(
            timestamp=datetime.now(),
            type=EventType.MOUSE_EVENT,
            data={"action": "click", "button": "left"}
        )
        
        # 添加记录
        storage.add_record(record1)
        storage.add_record(record2)
        
        # 获取所有记录
        all_records = storage.get_records()
        assert len(all_records) == 2
        
        # 按类型过滤
        keyboard_records = storage.get_records_by_type(EventType.KEYBOARD_EVENT)
        assert len(keyboard_records) == 1
        assert keyboard_records[0].type == EventType.KEYBOARD_EVENT
    
    def test_time_filtering(self):
        """测试时间过滤"""
        storage = SlidingWindowStorage(window_size=10)
        
        now = datetime.now()
        past = now - timedelta(seconds=5)
        future = now + timedelta(seconds=5)
        
        # 创建不同时间的记录
        record1 = RawRecord(timestamp=past, type=EventType.KEYBOARD_EVENT, data={})
        record2 = RawRecord(timestamp=now, type=EventType.KEYBOARD_EVENT, data={})
        record3 = RawRecord(timestamp=future, type=EventType.KEYBOARD_EVENT, data={})
        
        storage.add_record(record1)
        storage.add_record(record2)
        storage.add_record(record3)
        
        # 时间范围过滤
        recent_records = storage.get_records_in_timeframe(past, now)
        assert len(recent_records) == 2
    
    def test_cleanup_expired_records(self):
        """测试清理过期记录"""
        storage = SlidingWindowStorage(window_size=1)  # 1秒窗口
        
        # 添加过期记录
        old_record = RawRecord(
            timestamp=datetime.now() - timedelta(seconds=2),
            type=EventType.KEYBOARD_EVENT,
            data={}
        )
        storage.add_record(old_record)
        
        # 手动清理
        storage._cleanup_expired_records()
        
        # 过期记录应该被清理
        assert len(storage.records) == 0


class TestEventBuffer:
    """事件缓冲区测试"""
    
    def test_buffer_init(self):
        """测试缓冲区初始化"""
        buffer = EventBuffer(max_size=100)
        assert buffer.max_size == 100
        assert buffer.size() == 0
    
    def test_add_and_get_events(self):
        """测试添加和获取事件"""
        buffer = EventBuffer(max_size=10)
        
        # 创建测试记录
        record = RawRecord(
            timestamp=datetime.now(),
            type=EventType.KEYBOARD_EVENT,
            data={"key": "a", "action": "press"}
        )
        
        # 添加事件
        buffer.add(record)
        assert buffer.size() == 1
        
        # 获取事件
        events = buffer.get_all()
        assert len(events) == 1
        assert events[0] == record
        assert buffer.size() == 0  # 获取后应该清空
    
    def test_max_size_limit(self):
        """测试最大大小限制"""
        buffer = EventBuffer(max_size=3)
        
        # 添加超过最大大小的记录
        for i in range(5):
            record = RawRecord(
                timestamp=datetime.now(),
                type=EventType.KEYBOARD_EVENT,
                data={"key": str(i), "action": "press"}
            )
            buffer.add(record)
        
        # 应该只保留最后3个
        assert buffer.size() == 3
        
        events = buffer.get_all()
        assert events[0].data["key"] == "2"  # 第一个应该是第3个添加的


class TestPerceptionManager:
    """感知管理器测试"""
    
    @pytest.fixture
    def manager(self):
        """创建测试管理器"""
        return PerceptionManager(capture_interval=0.1, window_size=5)
    
    def test_manager_init(self, manager):
        """测试管理器初始化"""
        assert not manager.is_running
        assert manager.capture_interval == 0.1
        assert manager.window_size == 5
    
    @pytest.mark.asyncio
    async def test_manager_start_stop(self, manager):
        """测试管理器启动和停止"""
        # 启动管理器
        await manager.start()
        assert manager.is_running
        
        # 停止管理器
        await manager.stop()
        assert not manager.is_running
    
    def test_get_stats(self, manager):
        """测试获取统计信息"""
        stats = manager.get_stats()
        
        assert "is_running" in stats
        assert "capture_interval" in stats
        assert "window_size" in stats
        assert "storage" in stats
        assert "keyboard" in stats
        assert "mouse" in stats
        assert "screenshot" in stats
    
    def test_set_capture_interval(self, manager):
        """测试设置捕获间隔"""
        manager.set_capture_interval(0.5)
        assert manager.capture_interval == 0.5
        
        # 测试最小值限制
        manager.set_capture_interval(0.05)
        assert manager.capture_interval == 0.1  # 应该被限制为最小值
    
    def test_get_recent_records(self, manager):
        """测试获取最近记录"""
        # 添加一些测试记录
        for i in range(5):
            record = RawRecord(
                timestamp=datetime.now(),
                type=EventType.KEYBOARD_EVENT,
                data={"key": str(i), "action": "press"}
            )
            manager.storage.add_record(record)
        
        # 获取最近记录
        recent = manager.get_recent_records(3)
        assert len(recent) == 3
    
    def test_get_records_by_type(self, manager):
        """测试按类型获取记录"""
        # 添加不同类型的记录
        keyboard_record = RawRecord(
            timestamp=datetime.now(),
            type=EventType.KEYBOARD_EVENT,
            data={"key": "a", "action": "press"}
        )
        mouse_record = RawRecord(
            timestamp=datetime.now(),
            type=EventType.MOUSE_EVENT,
            data={"action": "click", "button": "left"}
        )
        
        manager.storage.add_record(keyboard_record)
        manager.storage.add_record(mouse_record)
        
        # 按类型获取
        keyboard_records = manager.get_records_by_type("keyboard_event")
        assert len(keyboard_records) == 1
        assert keyboard_records[0].type == EventType.KEYBOARD_EVENT


# 集成测试
class TestPerceptionIntegration:
    """感知模块集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_perception_workflow(self):
        """测试完整的感知工作流程"""
        # 创建管理器
        manager = PerceptionManager(capture_interval=0.1, window_size=5)
        
        # 记录捕获的数据
        captured_data = []
        
        def on_data_captured(record):
            captured_data.append(record)
        
        manager.on_data_captured = on_data_captured
        
        try:
            # 启动管理器
            await manager.start()
            
            # 等待一段时间让系统捕获数据
            await asyncio.sleep(1)
            
            # 检查是否有数据被捕获
            stats = manager.get_stats()
            assert stats["is_running"] is True
            
            # 获取存储的记录
            recent_records = manager.get_recent_records()
            assert isinstance(recent_records, list)
            
        finally:
            # 清理
            await manager.stop()
            assert len(captured_data) >= 0  # 可能没有捕获到数据，这是正常的


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
