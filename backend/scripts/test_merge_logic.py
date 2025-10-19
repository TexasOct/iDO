#!/usr/bin/env python3
"""
测试活动合并逻辑
专门测试LLM判断活动合并的功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.merger import ActivityMerger
from core.models import RawRecord, RecordType
from core.logger import get_logger

logger = get_logger(__name__)


async def test_merge_logic():
    """测试合并逻辑"""
    print("🧪 测试活动合并逻辑")
    print("=" * 60)
    
    # 创建合并器
    merger = ActivityMerger()
    
    # 测试案例1：相关活动（应该合并）
    print("\n📝 测试案例1：相关活动（应该合并）")
    print("-" * 40)
    
    # 模拟当前活动
    current_activity = {
        "id": "test-activity-1",
        "description": "用户在代码编辑器中编写Python代码",
        "start_time": datetime.now() - timedelta(minutes=5),
        "end_time": datetime.now() - timedelta(minutes=2),
        "source_events": [
            RawRecord(
                timestamp=datetime.now() - timedelta(minutes=2),
                type=RecordType.KEYBOARD_RECORD,
                data={"key": "Enter", "action": "press"}
            )
        ]
    }
    
    # 模拟新事件
    new_events = [
        RawRecord(
            timestamp=datetime.now() - timedelta(minutes=1),
            type=RecordType.KEYBOARD_RECORD,
            data={"key": "Tab", "action": "press"}
        ),
        RawRecord(
            timestamp=datetime.now() - timedelta(seconds=30),
            type=RecordType.MOUSE_RECORD,
            data={"action": "click", "button": "left", "position": [100, 200]}
        )
    ]
    
    # 测试合并判断
    should_merge, confidence = await merger.should_merge_activities(current_activity, new_events)
    print(f"应该合并: {should_merge}")
    print(f"置信度: {confidence:.2f}")
    
    # 显示当前活动描述
    current_summary = merger._get_current_activity_summary(current_activity)
    print(f"当前活动描述: {current_summary}")
    
    # 显示新事件描述
    new_summary = await merger._get_new_events_summary(new_events)
    print(f"新事件描述: {new_summary}")
    
    # 测试案例2：不相关活动（不应该合并）
    print("\n📝 测试案例2：不相关活动（不应该合并）")
    print("-" * 40)
    
    # 模拟当前活动
    current_activity2 = {
        "id": "test-activity-2",
        "description": "用户在浏览器中浏览网页",
        "start_time": datetime.now() - timedelta(minutes=5),
        "end_time": datetime.now() - timedelta(minutes=2),
        "source_events": [
            RawRecord(
                timestamp=datetime.now() - timedelta(minutes=2),
                type=RecordType.MOUSE_RECORD,
                data={"action": "scroll", "delta": [0, 100]}
            )
        ]
    }
    
    # 模拟新事件
    new_events2 = [
        RawRecord(
            timestamp=datetime.now() - timedelta(minutes=1),
            type=RecordType.KEYBOARD_RECORD,
            data={"key": "Ctrl", "action": "press", "modifiers": ["ctrl"]}
        ),
        RawRecord(
            timestamp=datetime.now() - timedelta(seconds=30),
            type=RecordType.KEYBOARD_RECORD,
            data={"key": "s", "action": "press", "modifiers": ["ctrl"]}
        )
    ]
    
    # 测试合并判断
    should_merge2, confidence2 = await merger.should_merge_activities(current_activity2, new_events2)
    print(f"应该合并: {should_merge2}")
    print(f"置信度: {confidence2:.2f}")
    
    # 测试案例3：时间间隔过长的活动（不应该合并）
    print("\n📝 测试案例3：时间间隔过长的活动（不应该合并）")
    print("-" * 40)
    
    # 模拟当前活动
    current_activity3 = {
        "id": "test-activity-3",
        "description": "用户在代码编辑器中编写Python代码",
        "start_time": datetime.now() - timedelta(hours=1),
        "end_time": datetime.now() - timedelta(minutes=55),
        "source_events": [
            RawRecord(
                timestamp=datetime.now() - timedelta(minutes=55),
                type=RecordType.KEYBOARD_RECORD,
                data={"key": "Enter", "action": "press"}
            )
        ]
    }
    
    # 模拟新事件（1小时后）
    new_events3 = [
        RawRecord(
            timestamp=datetime.now() - timedelta(minutes=5),
            type=RecordType.KEYBOARD_RECORD,
            data={"key": "Tab", "action": "press"}
        )
    ]
    
    # 测试合并判断
    should_merge3, confidence3 = await merger.should_merge_activities(current_activity3, new_events3)
    print(f"应该合并: {should_merge3}")
    print(f"置信度: {confidence3:.2f}")
    
    print(f"\n✅ 合并逻辑测试完成！")


if __name__ == "__main__":
    print("🧪 活动合并逻辑测试")
    print("这个测试将验证LLM判断活动合并的功能")
    print()
    
    try:
        asyncio.run(test_merge_logic())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n💥 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
