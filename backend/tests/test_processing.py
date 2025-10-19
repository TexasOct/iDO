"""
Processing 模块测试
测试事件筛选、总结、合并和持久化功能
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import EventType, RawRecord, Event
from processing.filter_rules import EventFilter
from processing.summarizer import EventSummarizer
from processing.merger import ActivityMerger
from processing.pipeline import ProcessingPipeline


class TestEventFilter:
    """事件筛选测试"""
    
    def test_filter_init(self):
        """测试筛选器初始化"""
        filter_obj = EventFilter()
        assert filter_obj.keyboard_special_keys is not None
        assert filter_obj.mouse_important_actions is not None
    
    def test_filter_keyboard_events(self):
        """测试键盘事件筛选"""
        filter_obj = EventFilter()
        
        # 创建测试记录
        records = [
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "a", "action": "press", "modifiers": []}
            ),
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "enter", "action": "press", "modifiers": []}
            ),
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "a", "action": "press", "modifiers": ["ctrl"]}
            )
        ]
        
        filtered = filter_obj.filter_keyboard_events(records)
        
        # 只有特殊键和带修饰键的应该被保留
        assert len(filtered) == 2
        assert filtered[0].data["key"] == "enter"
        assert filtered[1].data["modifiers"] == ["ctrl"]
    
    def test_filter_mouse_events(self):
        """测试鼠标事件筛选"""
        filter_obj = EventFilter()
        
        # 创建测试记录
        records = [
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.MOUSE_EVENT,
                data={"action": "move", "position": (100, 100)}
            ),
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.MOUSE_EVENT,
                data={"action": "press", "button": "left", "position": (100, 100)}
            ),
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.MOUSE_EVENT,
                data={"action": "scroll", "dx": 0, "dy": 10}
            )
        ]
        
        filtered = filter_obj.filter_mouse_events(records)
        
        # 只有重要动作应该被保留
        assert len(filtered) == 2
        assert filtered[0].data["action"] == "press"
        assert filtered[1].data["action"] == "scroll"
    
    def test_merge_consecutive_events(self):
        """测试连续事件合并"""
        filter_obj = EventFilter()
        
        # 创建连续事件
        base_time = datetime.now()
        records = [
            RawRecord(
                timestamp=base_time,
                type=EventType.KEYBOARD_EVENT,
                data={"key": "a", "action": "press", "modifiers": []}
            ),
            RawRecord(
                timestamp=base_time + timedelta(milliseconds=50),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "a", "action": "press", "modifiers": []}
            ),
            RawRecord(
                timestamp=base_time + timedelta(seconds=1),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "b", "action": "press", "modifiers": []}
            )
        ]
        
        merged = filter_obj.merge_consecutive_events(records)
        
        # 前两个应该被合并，第三个单独
        assert len(merged) == 2
        assert merged[0].data.get("merged", False) is True
        assert merged[0].data.get("count", 0) == 2


class TestEventSummarizer:
    """事件总结测试"""
    
    @pytest.fixture
    def summarizer(self):
        """创建总结器"""
        with patch('processing.summarizer.get_llm_client') as mock_llm:
            mock_client = Mock()
            mock_llm.return_value = mock_client
            return EventSummarizer(mock_client)
    
    def test_summarizer_init(self, summarizer):
        """测试总结器初始化"""
        assert summarizer.llm_client is not None
        assert summarizer.summary_cache == {}
    
    @pytest.mark.asyncio
    async def test_summarize_events_empty(self, summarizer):
        """测试空事件列表总结"""
        result = await summarizer.summarize_events([])
        assert result == "无事件"
    
    @pytest.mark.asyncio
    async def test_summarize_keyboard_events(self, summarizer):
        """测试键盘事件总结"""
        records = [
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "enter", "action": "press", "modifiers": []}
            ),
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "a", "action": "press", "modifiers": ["ctrl"]}
            )
        ]
        
        result = await summarizer.summarize_events(records)
        assert "键盘" in result
        assert "enter" in result
        assert "ctrl" in result
    
    @pytest.mark.asyncio
    async def test_summarize_mouse_events(self, summarizer):
        """测试鼠标事件总结"""
        records = [
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.MOUSE_EVENT,
                data={"action": "press", "button": "left", "position": (100, 100)}
            ),
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.MOUSE_EVENT,
                data={"action": "scroll", "dx": 0, "dy": 10}
            )
        ]
        
        result = await summarizer.summarize_events(records)
        assert "鼠标" in result
        assert "点击" in result
        assert "滚动" in result
    
    def test_analyze_activity_pattern(self, summarizer):
        """测试活动模式分析"""
        records = [
            RawRecord(
                timestamp=datetime.now(),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "a", "action": "press"}
            ),
            RawRecord(
                timestamp=datetime.now() + timedelta(seconds=1),
                type=EventType.MOUSE_EVENT,
                data={"action": "press", "button": "left"}
            )
        ]
        
        pattern = summarizer._analyze_activity_pattern(records)
        
        assert pattern["total_events"] == 2
        assert pattern["keyboard_activity"] == 1
        assert pattern["mouse_activity"] == 1
        assert pattern["time_span"] > 0


class TestActivityMerger:
    """活动合并测试"""
    
    @pytest.fixture
    def merger(self):
        """创建合并器"""
        with patch('processing.merger.get_llm_client') as mock_llm:
            mock_client = Mock()
            mock_llm.return_value = mock_client
            return ActivityMerger(mock_client)
    
    def test_merger_init(self, merger):
        """测试合并器初始化"""
        assert merger.llm_client is not None
        assert merger.merge_threshold == 0.7
        assert merger.time_threshold == 300
    
    def test_is_within_time_threshold(self, merger):
        """测试时间阈值检查"""
        current_activity = {
            "end_time": datetime.now()
        }
        
        new_events = [
            RawRecord(
                timestamp=datetime.now() + timedelta(seconds=100),
                type=EventType.KEYBOARD_EVENT,
                data={"key": "a", "action": "press"}
            )
        ]
        
        # 100秒内应该返回True
        result = merger._is_within_time_threshold(current_activity, new_events)
        assert result is True
        
        # 超过阈值应该返回False
        new_events[0].timestamp = datetime.now() + timedelta(seconds=400)
        result = merger._is_within_time_threshold(current_activity, new_events)
        assert result is False
    
    def test_extract_activity_features(self, merger):
        """测试活动特征提取"""
        activity = {
            "event_count": 10,
            "start_time": datetime.now() - timedelta(minutes=5),
            "end_time": datetime.now(),
            "source_events": [
                RawRecord(
                    timestamp=datetime.now(),
                    type=EventType.KEYBOARD_EVENT,
                    data={"key": "a", "action": "press"}
                )
            ]
        }
        
        features = merger._extract_activity_features(activity)
        
        assert features["event_count"] == 10
        assert features["time_span"] > 0
        assert features["keyboard_ratio"] == 1.0
    
    def test_calculate_single_feature_similarity(self, merger):
        """测试单特征相似度计算"""
        # 相同值
        assert merger._calculate_single_feature_similarity("typing", "typing") == 1.0
        
        # 不同字符串
        assert merger._calculate_single_feature_similarity("typing", "navigation") == 0.0
        
        # 数值相似度
        assert merger._calculate_single_feature_similarity(0.5, 0.6) > 0.8
        assert merger._calculate_single_feature_similarity(0.5, 1.0) < 0.6
    


class TestProcessingPipeline:
    """处理管道测试"""
    
    @pytest.fixture
    def pipeline(self):
        """创建处理管道"""
        with patch('processing.pipeline.ProcessingPersistence') as mock_persistence:
            mock_persistence.return_value = Mock()
            return ProcessingPipeline(processing_interval=1)
    
    def test_pipeline_init(self, pipeline):
        """测试管道初始化"""
        assert pipeline.processing_interval == 1
        assert pipeline.is_running is False
        assert pipeline.current_activity is None
    
    @pytest.mark.asyncio
    async def test_pipeline_start_stop(self, pipeline):
        """测试管道启动和停止"""
        await pipeline.start()
        assert pipeline.is_running is True
        
        await pipeline.stop()
        assert pipeline.is_running is False
    
    @pytest.mark.asyncio
    async def test_process_empty_records(self, pipeline):
        """测试处理空记录"""
        result = await pipeline.process_raw_records([])
        assert result["events"] == []
        assert result["activities"] == []
        assert result["merged"] is False
    
    @pytest.mark.asyncio
    async def test_group_records_by_time(self, pipeline):
        """测试按时间分组记录"""
        base_time = datetime.now()
        records = [
            RawRecord(timestamp=base_time, type=EventType.KEYBOARD_EVENT, data={}),
            RawRecord(timestamp=base_time + timedelta(seconds=5), type=EventType.KEYBOARD_EVENT, data={}),
            RawRecord(timestamp=base_time + timedelta(seconds=15), type=EventType.KEYBOARD_EVENT, data={})
        ]
        
        groups = pipeline._group_records_by_time(records, 10)
        
        # 应该分为两组：前两个一组，第三个一组
        assert len(groups) == 2
        assert len(groups[0]) == 2
        assert len(groups[1]) == 1
    
    def test_get_stats(self, pipeline):
        """测试获取统计信息"""
        stats = pipeline.get_stats()
        
        assert "is_running" in stats
        assert "processing_interval" in stats
        assert "current_activity" in stats
        assert "stats" in stats
    
    def test_set_processing_interval(self, pipeline):
        """测试设置处理间隔"""
        pipeline.set_processing_interval(5)
        assert pipeline.processing_interval == 5
        
        # 测试最小值限制
        pipeline.set_processing_interval(0)
        assert pipeline.processing_interval == 1


# 集成测试
class TestProcessingIntegration:
    """处理模块集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_processing_workflow(self):
        """测试完整处理工作流程"""
        with patch('processing.pipeline.ProcessingPersistence') as mock_persistence:
            mock_persistence.return_value = Mock()
            pipeline = ProcessingPipeline(processing_interval=1)
            
            # 创建测试记录
            records = [
                RawRecord(
                    timestamp=datetime.now(),
                    type=EventType.KEYBOARD_EVENT,
                    data={"key": "enter", "action": "press", "modifiers": []}
                ),
                RawRecord(
                    timestamp=datetime.now(),
                    type=EventType.MOUSE_EVENT,
                    data={"action": "press", "button": "left", "position": (100, 100)}
                )
            ]
            
            # 处理记录
            result = await pipeline.process_raw_records(records)
            
            # 验证结果
            assert "events" in result
            assert "activities" in result
            assert "merged" in result
            assert isinstance(result["events"], list)
            assert isinstance(result["activities"], list)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
