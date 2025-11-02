#!/usr/bin/env python3
"""
测试活动处理逻辑
专门测试新的顺序遍历events并逐个判断合并的功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.pipeline import ProcessingPipeline
from core.models import RawRecord, Event, RecordType
from core.logger import get_logger

logger = get_logger(__name__)


async def test_activity_processing():
    """测试活动处理逻辑"""
    print("🧪 测试活动处理逻辑")
    print("=" * 60)
    
    # 创建处理管道
    pipeline = ProcessingPipeline()
    await pipeline.start()
    
    try:
        # 创建模拟的events
        events = []
        
        # Event 1: 代码编辑
        event1 = Event(
            id="event-1",
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now() - timedelta(minutes=4),
            type=RecordType.KEYBOARD_RECORD,
            summary="用户在代码编辑器中编写Python函数",
            source_data=[]
        )
        events.append(event1)
        
        # Event 2: 继续代码编辑（应该合并）
        event2 = Event(
            id="event-2",
            start_time=datetime.now() - timedelta(minutes=4),
            end_time=datetime.now() - timedelta(minutes=3),
            type=RecordType.KEYBOARD_RECORD,
            summary="用户继续编写同一个Python函数的其他部分",
            source_data=[]
        )
        events.append(event2)
        
        # Event 3: 运行测试（可能不合并）
        event3 = Event(
            id="event-3",
            start_time=datetime.now() - timedelta(minutes=3),
            end_time=datetime.now() - timedelta(minutes=2),
            type=RecordType.KEYBOARD_RECORD,
            summary="用户在终端中运行测试命令",
            source_data=[]
        )
        events.append(event3)
        
        # Event 4: 查看结果（可能合并到测试）
        event4 = Event(
            id="event-4",
            start_time=datetime.now() - timedelta(minutes=2),
            end_time=datetime.now() - timedelta(minutes=1),
            type=RecordType.MOUSE_RECORD,
            summary="用户查看测试运行结果",
            source_data=[]
        )
        events.append(event4)
        
        print(f"📝 创建了 {len(events)} 个测试事件")
        for i, event in enumerate(events, 1):
            print(f"   {i}. {event.summary}")
        
        print(f"\n🔄 开始处理活动...")
        print("=" * 60)
        
        # 处理events
        result = await pipeline._process_activities(events)
        
        print(f"\n📊 处理结果:")
        print(f"   - 生成活动数: {len(result['activities'])}")
        print(f"   - 是否合并: {result['merged']}")
        print(f"   - 当前活动: {'有' if pipeline.current_activity else '无'}")
        
        # 显示生成的活动
        if result['activities']:
            print(f"\n📋 生成的活动:")
            for i, activity in enumerate(result['activities'], 1):
                print(f"   {i}. {activity['description']}")
                print(f"      时间: {activity['start_time'].strftime('%H:%M:%S')} - {activity['end_time'].strftime('%H:%M:%S')}")
                print(f"      事件数: {activity['event_count']}")
        
        # 显示当前活动
        if pipeline.current_activity:
            print(f"\n🎯 当前活动:")
            print(f"   - 描述: {pipeline.current_activity['description']}")
            print(f"   - 时间: {pipeline.current_activity['start_time'].strftime('%H:%M:%S')} - {pipeline.current_activity['end_time'].strftime('%H:%M:%S')}")
            print(f"   - 事件数: {pipeline.current_activity['event_count']}")
        
        print(f"\n✅ 活动处理测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await pipeline.stop()


if __name__ == "__main__":
    print("🧪 活动处理逻辑测试")
    print("这个测试将验证新的顺序遍历events并逐个判断合并的功能")
    print()
    
    try:
        asyncio.run(test_activity_processing())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n💥 测试失败: {e}")
        sys.exit(1)
