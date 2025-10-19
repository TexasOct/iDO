"""
Perception 模块模拟测试
不需要系统权限的测试版本
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
from perception.storage import SlidingWindowStorage, EventBuffer


class TestSlidingWindowStorageMock:
    """滑动窗口存储测试（不需要权限）"""
    
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


class TestEventBufferMock:
    """事件缓冲区测试（不需要权限）"""
    
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


class TestPerceptionManagerMock:
    """感知管理器模拟测试（不需要权限）"""
    
    @pytest.fixture
    def mock_manager(self):
        """创建模拟管理器"""
        with patch('perception.manager.KeyboardCapture') as mock_kb, \
             patch('perception.manager.MouseCapture') as mock_mouse, \
             patch('perception.manager.ScreenshotCapture') as mock_screenshot:
            
            # 模拟捕获器
            mock_kb.return_value.is_running = False
            mock_mouse.return_value.is_running = False
            mock_screenshot.return_value.is_running = False
            
            from perception.manager import PerceptionManager
            manager = PerceptionManager(capture_interval=0.1, window_size=5)
            return manager
    
    def test_manager_init(self, mock_manager):
        """测试管理器初始化"""
        assert not mock_manager.is_running
        assert mock_manager.capture_interval == 0.1
        assert mock_manager.window_size == 5
    
    def test_get_stats(self, mock_manager):
        """测试获取统计信息"""
        stats = mock_manager.get_stats()
        
        assert "is_running" in stats
        assert "capture_interval" in stats
        assert "window_size" in stats
        assert "storage" in stats
    
    def test_set_capture_interval(self, mock_manager):
        """测试设置捕获间隔"""
        mock_manager.set_capture_interval(0.5)
        assert mock_manager.capture_interval == 0.5
        
        # 测试最小值限制
        mock_manager.set_capture_interval(0.05)
        assert mock_manager.capture_interval == 0.1  # 应该被限制为最小值


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])

