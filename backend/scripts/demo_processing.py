#!/usr/bin/env python3
"""
Processing 模块演示脚本
展示事件筛选、总结、合并和持久化功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import RawRecord, RecordType
from processing.pipeline import ProcessingPipeline
from core.logger import get_logger

logger = get_logger(__name__)


async def demo_processing():
    """演示处理模块功能"""
    print("🔄 启动 Rewind Processing 演示...")
    print("=" * 50)
    
    # 创建处理管道
    pipeline = ProcessingPipeline()
    
    try:
        # 启动管道
        print("📡 启动处理管道...")
        await pipeline.start()
        
        print("✅ 处理管道已启动！")
        print("\n📋 模拟用户交互数据...")
        print("=" * 50)
        
        # 模拟不同类型的用户交互数据
        test_records = create_test_records()
        
        print(f"📊 创建了 {len(test_records)} 条测试记录")
        
        # 分批处理数据
        batch_size = 5
        for i in range(0, len(test_records), batch_size):
            batch = test_records[i:i + batch_size]
            print(f"\n🔄 处理第 {i//batch_size + 1} 批数据 ({len(batch)} 条记录)...")
            
            # 处理记录
            result = await pipeline.process_raw_records(batch)
            
            # 显示结果
            print(f"   ✅ 创建了 {len(result['events'])} 个事件")
            print(f"   ✅ 创建了 {len(result['activities'])} 个活动")
            print(f"   {'🔄 合并到现有活动' if result['merged'] else '🆕 创建新活动'}")
            
            # 显示事件详情
            for event in result['events']:
                print(f"      📝 事件: {event.type.value} - {event.summary}")
            
            # 显示活动详情
            for activity in result['activities']:
                print(f"      🎯 活动: {activity['description']}")
        
        # 显示最终统计
        print("\n" + "=" * 50)
        print("📈 处理完成统计:")
        stats = pipeline.get_stats()
        print(f"   - 总处理记录数: {stats['stats']['total_processed']}")
        print(f"   - 创建事件数: {stats['stats']['events_created']}")
        print(f"   - 创建活动数: {stats['stats']['activities_created']}")
        print(f"   - 合并活动数: {stats['stats']['activities_merged']}")
        
        # 获取最近的活动
        recent_activities = await pipeline.get_recent_activities(5)
        if recent_activities:
            print(f"\n📋 最近 {len(recent_activities)} 个活动:")
            for i, activity in enumerate(recent_activities, 1):
                print(f"   {i}. {activity['description']}")
                print(f"      时间: {activity['start_time']} - {activity['end_time']}")
                print(f"      事件数: {activity.get('event_count', 0)}")
        
        # 获取最近的事件
        recent_events = await pipeline.get_recent_events(10)
        if recent_events:
            print(f"\n📝 最近 {len(recent_events)} 个事件:")
            for i, event in enumerate(recent_events, 1):
                print(f"   {i}. [{event.type.value}] {event.summary}")
                print(f"      时间: {event.start_time} - {event.end_time}")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        logger.error(f"演示错误: {e}")
    finally:
        # 停止管道
        print("\n🛑 停止处理管道...")
        await pipeline.stop()
        print("✅ 演示结束！")


def create_test_records():
    """创建测试记录"""
    base_time = datetime.now()
    records = []
    
    # 模拟打字活动
    typing_keys = ['h', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd']
    for i, key in enumerate(typing_keys):
        records.append(RawRecord(
            timestamp=base_time + timedelta(seconds=i * 0.5),
            type=RecordType.KEYBOARD_RECORD,
            data={"key": key, "action": "press", "modifiers": [], "key_type": "char"}
        ))
    
    # 模拟特殊键操作
    records.append(RawRecord(
        timestamp=base_time + timedelta(seconds=6),
        type=EventType.KEYBOARD_EVENT,
        data={"key": "enter", "action": "press", "modifiers": [], "key_type": "special"}
    ))
    
    # 模拟鼠标操作
    mouse_actions = [
        ("press", "left", (100, 200)),
        ("release", "left", (100, 200)),
        ("press", "left", (150, 250)),
        ("drag", "left", (200, 300)),
        ("drag_end", "left", (250, 350))
    ]
    
    for i, (action, button, pos) in enumerate(mouse_actions):
        records.append(RawRecord(
            timestamp=base_time + timedelta(seconds=7 + i * 0.3),
            type=RecordType.MOUSE_RECORD,
            data={"action": action, "button": button, "position": pos}
        ))
    
    # 模拟滚动操作
    for i in range(3):
        records.append(RawRecord(
            timestamp=base_time + timedelta(seconds=9 + i * 0.1),
            type=RecordType.MOUSE_RECORD,
            data={"action": "scroll", "dx": 0, "dy": 10, "position": (200, 300)}
        ))
    
    # 模拟屏幕截图
    for i in range(2):
        records.append(RawRecord(
            timestamp=base_time + timedelta(seconds=10 + i * 2),
            type=RecordType.SCREENSHOT_RECORD,
            data={
                "action": "capture",
                "width": 1920,
                "height": 1080,
                "format": "JPEG",
                "size_bytes": 200000,
                "hash": f"screenshot_{i}"
            }
        ))
    
    # 模拟组合键操作
    records.append(RawRecord(
        timestamp=base_time + timedelta(seconds=15),
        type=EventType.KEYBOARD_EVENT,
        data={"key": "c", "action": "press", "modifiers": ["ctrl"], "key_type": "char"}
    ))
    
    records.append(RawRecord(
        timestamp=base_time + timedelta(seconds=16),
        type=EventType.KEYBOARD_EVENT,
        data={"key": "v", "action": "press", "modifiers": ["ctrl"], "key_type": "char"}
    ))
    
    # 模拟另一个活动（浏览网页）
    browse_time = base_time + timedelta(seconds=20)
    browse_actions = [
        ("press", "left", (300, 400)),
        ("release", "left", (300, 400)),
        ("scroll", "middle", (300, 400)),
        ("scroll", "middle", (300, 400)),
        ("press", "left", (400, 500)),
        ("release", "left", (400, 500))
    ]
    
    for i, (action, button, pos) in enumerate(browse_actions):
        records.append(RawRecord(
            timestamp=browse_time + timedelta(seconds=i * 0.5),
            type=RecordType.MOUSE_RECORD,
            data={"action": action, "button": button, "position": pos}
        ))
    
    return records


if __name__ == "__main__":
    print("🎯 Rewind Processing 模块演示")
    print("这个演示将展示事件筛选、总结、合并和持久化功能")
    print()
    
    try:
        asyncio.run(demo_processing())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n💥 演示失败: {e}")
        sys.exit(1)
