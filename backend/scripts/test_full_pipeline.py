#!/usr/bin/env python3
"""
完整管道测试脚本
测试感知、处理、总结的完整流程
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


async def test_full_pipeline():
    """测试完整管道功能"""
    print("🚀 启动 Rewind 完整管道测试...")
    print("=" * 60)
    
    # 创建处理管道
    pipeline = ProcessingPipeline()
    
    try:
        # 启动管道
        print("📡 启动处理管道...")
        await pipeline.start()
        print("✅ 处理管道已启动！")
        
        # 创建测试数据
        print("\n📋 创建测试数据...")
        test_records = create_comprehensive_test_records()
        print(f"✅ 创建了 {len(test_records)} 条测试记录")
        
        # 分批处理数据，模拟真实的时间间隔
        print("\n🔄 开始处理数据...")
        print("=" * 60)
        
        batch_size = 8
        for i in range(0, len(test_records), batch_size):
            batch = test_records[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            print(f"\n📦 处理第 {batch_num} 批数据 ({len(batch)} 条记录)...")
            
            # 显示这批数据的内容
            for record in batch:
                timestamp = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
                if record.type == RecordType.KEYBOARD_RECORD:
                    key = record.data.get("key", "unknown")
                    action = record.data.get("action", "unknown")
                    modifiers = record.data.get("modifiers", [])
                    mod_str = f" +{'+'.join(modifiers)}" if modifiers else ""
                    print(f"   ⌨️  [{timestamp}] 键盘: {key}{mod_str} ({action})")
                elif record.type == RecordType.MOUSE_RECORD:
                    action = record.data.get("action", "unknown")
                    button = record.data.get("button", "unknown")
                    if "position" in record.data:
                        pos = record.data["position"]
                        print(f"   🖱️  [{timestamp}] 鼠标: {action} ({button}) at {pos}")
                    else:
                        print(f"   🖱️  [{timestamp}] 鼠标: {action} ({button})")
                elif record.type == RecordType.SCREENSHOT_RECORD:
                    width = record.data.get("width", 0)
                    height = record.data.get("height", 0)
                    print(f"   📸 [{timestamp}] 截图: {width}x{height}")
            
            # 处理记录
            print(f"\n🔄 正在处理第 {batch_num} 批...")
            result = await pipeline.process_raw_records(batch)
            
            # 显示处理结果
            print(f"   ✅ 创建了 {len(result['events'])} 个事件")
            print(f"   ✅ 创建了 {len(result['activities'])} 个活动")
            print(f"   {'🔄 合并到现有活动' if result['merged'] else '🆕 创建新活动'}")
            
            # 显示事件详情
            for event in result['events']:
                print(f"      📝 事件: [{event.type.value}] {event.summary}")
                print(f"         时间: {event.start_time.strftime('%H:%M:%S')} - {event.end_time.strftime('%H:%M:%S')}")
                print(f"         源数据: {len(event.source_data)} 条记录")
            
            # 显示活动详情
            for activity in result['activities']:
                print(f"      🎯 活动: {activity['description']}")
                print(f"         时间: {activity['start_time'].strftime('%H:%M:%S')} - {activity['end_time'].strftime('%H:%M:%S')}")
                print(f"         事件数: {activity.get('event_count', 0)}")
            
            # 等待一段时间，模拟真实的时间间隔
            if i + batch_size < len(test_records):
                print(f"\n⏱️  等待 2 秒后处理下一批...")
                await asyncio.sleep(2)
        
        # 显示最终统计
        print("\n" + "=" * 60)
        print("📈 处理完成统计:")
        stats = pipeline.get_stats()
        print(f"   - 总处理记录数: {stats['stats']['total_processed']}")
        print(f"   - 创建事件数: {stats['stats']['events_created']}")
        print(f"   - 创建活动数: {stats['stats']['activities_created']}")
        print(f"   - 合并活动数: {stats['stats']['activities_merged']}")
        
        # 获取最近的活动
        print(f"\n📋 最近的活动:")
        recent_activities = await pipeline.get_recent_activities(5)
        if recent_activities:
            for i, activity in enumerate(recent_activities, 1):
                print(f"   {i}. {activity['description']}")
                print(f"      时间: {activity['start_time'].strftime('%H:%M:%S')} - {activity['end_time'].strftime('%H:%M:%S')}")
                print(f"      事件数: {activity.get('event_count', 0)}")
        else:
            print("   无活动数据")
        
        # 获取最近的事件
        print(f"\n📝 最近的事件:")
        recent_events = await pipeline.get_recent_events(10)
        if recent_events:
            for i, event in enumerate(recent_events, 1):
                print(f"   {i}. [{event.type.value}] {event.summary}")
                print(f"      时间: {event.start_time.strftime('%H:%M:%S')} - {event.end_time.strftime('%H:%M:%S')}")
                print(f"      源数据: {len(event.source_data)} 条记录")
        else:
            print("   无事件数据")
        
        print(f"\n✅ 完整管道测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        logger.error(f"测试错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 停止管道
        print("\n🛑 停止处理管道...")
        await pipeline.stop()
        print("✅ 测试结束！")


def create_comprehensive_test_records():
    """创建综合测试记录"""
    base_time = datetime.now()
    records = []
    
    # 场景1: 编写文档活动
    print("   📝 创建场景1: 编写文档活动")
    doc_time = base_time
    doc_text = "Hello World! This is a test document."
    
    for i, char in enumerate(doc_text):
        records.append(RawRecord(
            timestamp=doc_time + timedelta(seconds=i * 0.1),
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": char,
                "action": "press",
                "modifiers": [],
                "key_type": "char"
            }
        ))
    
    # 添加回车
    records.append(RawRecord(
        timestamp=doc_time + timedelta(seconds=len(doc_text) * 0.1 + 0.5),
        type=RecordType.KEYBOARD_RECORD,
        data={
            "key": "enter",
            "action": "press",
            "modifiers": [],
            "key_type": "special"
        }
    ))
    
    # 添加截图
    records.append(RawRecord(
        timestamp=doc_time + timedelta(seconds=len(doc_text) * 0.1 + 1),
        type=RecordType.SCREENSHOT_RECORD,
        data={
            "action": "capture",
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "size_bytes": 250000,
            "file_path": f"/tmp/screenshot_{len(records)}.jpg"
        }
    ))
    
    # 场景2: 复制粘贴操作
    print("   📋 创建场景2: 复制粘贴操作")
    copy_time = base_time + timedelta(seconds=10)
    
    # 选择文本 (Ctrl+A)
    records.append(RawRecord(
        timestamp=copy_time,
        type=RecordType.KEYBOARD_RECORD,
        data={
            "key": "a",
            "action": "press",
            "modifiers": ["ctrl"],
            "key_type": "char"
        }
    ))
    
    # 复制 (Ctrl+C)
    records.append(RawRecord(
        timestamp=copy_time + timedelta(seconds=0.2),
        type=RecordType.KEYBOARD_RECORD,
        data={
            "key": "c",
            "action": "press",
            "modifiers": ["ctrl"],
            "key_type": "char"
        }
    ))
    
    # 鼠标点击新位置
    records.append(RawRecord(
        timestamp=copy_time + timedelta(seconds=0.5),
        type=RecordType.MOUSE_RECORD,
        data={
            "action": "press",
            "button": "left",
            "position": [300, 400]
        }
    ))
    
    records.append(RawRecord(
        timestamp=copy_time + timedelta(seconds=0.6),
        type=RecordType.MOUSE_RECORD,
        data={
            "action": "release",
            "button": "left",
            "position": [300, 400]
        }
    ))
    
    # 粘贴 (Ctrl+V)
    records.append(RawRecord(
        timestamp=copy_time + timedelta(seconds=0.8),
        type=RecordType.KEYBOARD_RECORD,
        data={
            "key": "v",
            "action": "press",
            "modifiers": ["ctrl"],
            "key_type": "char"
        }
    ))
    
    # 场景3: 网页浏览活动
    print("   🌐 创建场景3: 网页浏览活动")
    browse_time = base_time + timedelta(seconds=20)
    
    # 鼠标滚动
    for i in range(5):
        records.append(RawRecord(
            timestamp=browse_time + timedelta(seconds=i * 0.3),
            type=RecordType.MOUSE_RECORD,
            data={
                "action": "scroll",
                "button": "middle",
                "position": [500, 300],
                "delta": [0, -50]
            }
        ))
    
    # 点击链接
    records.append(RawRecord(
        timestamp=browse_time + timedelta(seconds=2),
        type=RecordType.MOUSE_RECORD,
        data={
            "action": "press",
            "button": "left",
            "position": [400, 200]
        }
    ))
    
    records.append(RawRecord(
        timestamp=browse_time + timedelta(seconds=2.1),
        type=RecordType.MOUSE_RECORD,
        data={
            "action": "release",
            "button": "left",
            "position": [400, 200]
        }
    ))
    
    # 添加截图
    records.append(RawRecord(
        timestamp=browse_time + timedelta(seconds=3),
        type=RecordType.SCREENSHOT_RECORD,
        data={
            "action": "capture",
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "size_bytes": 300000,
            "file_path": f"/tmp/screenshot_{len(records)}.jpg"
        }
    ))
    
    # 场景4: 代码编辑活动
    print("   💻 创建场景4: 代码编辑活动")
    code_time = base_time + timedelta(seconds=30)
    
    # 输入代码
    code_lines = [
        "def hello_world():",
        "    print('Hello, World!')",
        "    return True"
    ]
    
    for line_num, line in enumerate(code_lines):
        for char_num, char in enumerate(line):
            records.append(RawRecord(
                timestamp=code_time + timedelta(seconds=line_num * 2 + char_num * 0.05),
                type=RecordType.KEYBOARD_RECORD,
                data={
                    "key": char,
                    "action": "press",
                    "modifiers": [],
                    "key_type": "char"
                }
            ))
        
        # 每行结束后按回车
        records.append(RawRecord(
            timestamp=code_time + timedelta(seconds=line_num * 2 + len(line) * 0.05 + 0.1),
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": "enter",
                "action": "press",
                "modifiers": [],
                "key_type": "special"
            }
        ))
    
    # 保存文件 (Ctrl+S)
    records.append(RawRecord(
        timestamp=code_time + timedelta(seconds=8),
        type=RecordType.KEYBOARD_RECORD,
        data={
            "key": "s",
            "action": "press",
            "modifiers": ["ctrl"],
            "key_type": "char"
        }
    ))
    
    # 添加截图
    records.append(RawRecord(
        timestamp=code_time + timedelta(seconds=9),
        type=RecordType.SCREENSHOT_RECORD,
        data={
            "action": "capture",
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "size_bytes": 280000,
            "file_path": f"/tmp/screenshot_{len(records)}.jpg"
        }
    ))
    
    print(f"   ✅ 总共创建了 {len(records)} 条记录")
    return records


if __name__ == "__main__":
    print("🎯 Rewind 完整管道测试")
    print("这个测试将展示感知、处理、总结的完整流程")
    print("包括事件筛选、LLM总结、活动合并等功能")
    print()
    
    try:
        asyncio.run(test_full_pipeline())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n💥 测试失败: {e}")
        sys.exit(1)
