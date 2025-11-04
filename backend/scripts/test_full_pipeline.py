#!/usr/bin/env python3
"""
Full pipeline test script
Test the complete process of perception, processing, and summarization
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import RawRecord, RecordType
from processing.pipeline import ProcessingPipeline
from core.logger import get_logger

logger = get_logger(__name__)


async def test_full_pipeline():
    """Test complete pipeline functionality"""
    print("🚀 Starting Rewind Full Pipeline Test...")
    print("=" * 60)

    # Create processing pipeline
    pipeline = ProcessingPipeline()

    try:
        # Start pipeline
        print("📡 Starting processing pipeline...")
        await pipeline.start()
        print("✅ Processing pipeline started!")

        # Create test data
        print("\n📋 Creating test data...")
        test_records = create_comprehensive_test_records()
        print(f"✅ Created {len(test_records)} test records")

        # Process data in batches, simulating real time intervals
        print("\n🔄 Starting data processing...")
        print("=" * 60)

        batch_size = 8
        for i in range(0, len(test_records), batch_size):
            batch = test_records[i : i + batch_size]
            batch_num = i // batch_size + 1

            print(f"\n📦 Processing batch {batch_num} data ({len(batch)} records)...")

            # Display the content of this batch
            for record in batch:
                timestamp = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
                if record.type == RecordType.KEYBOARD_RECORD:
                    key = record.data.get("key", "unknown")
                    action = record.data.get("action", "unknown")
                    modifiers = record.data.get("modifiers", [])
                    mod_str = f" +{'+'.join(modifiers)}" if modifiers else ""
                    print(f"   ⌨️  [{timestamp}] Keyboard: {key}{mod_str} ({action})")
                elif record.type == RecordType.MOUSE_RECORD:
                    action = record.data.get("action", "unknown")
                    button = record.data.get("button", "unknown")
                    if "position" in record.data:
                        pos = record.data["position"]
                        print(
                            f"   🖱️  [{timestamp}] Mouse: {action} ({button}) at {pos}"
                        )
                    else:
                        print(f"   🖱️  [{timestamp}] Mouse: {action} ({button})")
                elif record.type == RecordType.SCREENSHOT_RECORD:
                    width = record.data.get("width", 0)
                    height = record.data.get("height", 0)
                    print(f"   📸 [{timestamp}] Screenshot: {width}x{height}")

            # Process records
            print(f"\n🔄 Processing batch {batch_num}...")
            result = await pipeline.process_raw_records(batch)

            # Display processing results
            print(f"   ✅ Created {len(result['events'])} events")
            print(f"   ✅ Created {len(result['activities'])} activities")
            print(
                f"   {'🔄 Merged into existing activity' if result['merged'] else '🆕 Created new activity'}"
            )

            # Display event details
            for event in result["events"]:
                print(f"      📝 Event: [{event.type.value}] {event.summary}")
                print(
                    f"         Time: {event.start_time.strftime('%H:%M:%S')} - {event.end_time.strftime('%H:%M:%S')}"
                )
                print(f"         Source data: {len(event.source_data)} records")

            # Display activity details
            for activity in result["activities"]:
                print(f"      🎯 Activity: {activity['description']}")
                print(
                    f"         Time: {activity['start_time'].strftime('%H:%M:%S')} - {activity['end_time'].strftime('%H:%M:%S')}"
                )
                print(f"         Event count: {activity.get('event_count', 0)}")

            # Wait for a while to simulate real time intervals
            if i + batch_size < len(test_records):
                print(f"\n⏱️  Waiting 2 seconds before processing next batch...")
                await asyncio.sleep(2)

        # Display final statistics
        print("\n" + "=" * 60)
        print("📈 Processing completion statistics:")
        stats = pipeline.get_stats()
        print(f"   - Total processed records: {stats['stats']['total_processed']}")
        print(f"   - Created events: {stats['stats']['events_created']}")
        print(f"   - Created activities: {stats['stats']['activities_created']}")
        print(f"   - Merged activities: {stats['stats']['activities_merged']}")

        # 获取最近的活动
        print(f"\n📋 Recent activities:")
        recent_activities = await pipeline.get_recent_activities(5)
        if recent_activities:
            for i, activity in enumerate(recent_activities, 1):
                print(f"   {i}. {activity['description']}")
                print(
                    f"      Time: {activity['start_time'].strftime('%H:%M:%S')} - {activity['end_time'].strftime('%H:%M:%S')}"
                )
                print(f"      Event count: {activity.get('event_count', 0)}")
        else:
            print("   No activity data")

        # 获取最近的事件
        print(f"\n📝 Recent events:")
        recent_events = await pipeline.get_recent_events(10)
        if recent_events:
            for i, event in enumerate(recent_events, 1):
                print(f"   {i}. [{event.type.value}] {event.summary}")
                print(
                    f"      Time: {event.start_time.strftime('%H:%M:%S')} - {event.end_time.strftime('%H:%M:%S')}"
                )
                print(f"      Source data: {len(event.source_data)} records")
        else:
            print("   No event data")

        print(f"\n✅ Complete pipeline test completed!")

    except Exception as e:
        print(f"\n❌ Error occurred during test: {e}")
        logger.error(f"Test error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 停止管道
        print("\n🛑 Stopping processing pipeline...")
        await pipeline.stop()
        print("✅ Test completed!")


def create_comprehensive_test_records():
    """Create comprehensive test records"""
    base_time = datetime.now()
    records = []

    # Scene 1: Writing document activity
    print("   📝 Creating scene 1: Writing document activity")
    doc_time = base_time
    doc_text = "Hello World! This is a test document."

    for i, char in enumerate(doc_text):
        records.append(
            RawRecord(
                timestamp=doc_time + timedelta(seconds=i * 0.1),
                type=RecordType.KEYBOARD_RECORD,
                data={
                    "key": char,
                    "action": "press",
                    "modifiers": [],
                    "key_type": "char",
                },
            )
        )

    # Add carriage return
    records.append(
        RawRecord(
            timestamp=doc_time + timedelta(seconds=len(doc_text) * 0.1 + 0.5),
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": "enter",
                "action": "press",
                "modifiers": [],
                "key_type": "special",
            },
        )
    )

    # Add screenshot
    records.append(
        RawRecord(
            timestamp=doc_time + timedelta(seconds=len(doc_text) * 0.1 + 1),
            type=RecordType.SCREENSHOT_RECORD,
            data={
                "action": "capture",
                "width": 1920,
                "height": 1080,
                "format": "JPEG",
                "size_bytes": 250000,
                "file_path": f"/tmp/screenshot_{len(records)}.jpg",
            },
        )
    )

    # Scene 2: Copy and paste operation
    print("   📋 Creating scene 2: Copy and paste operation")
    copy_time = base_time + timedelta(seconds=10)

    # Select text (Ctrl+A)
    records.append(
        RawRecord(
            timestamp=copy_time,
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": "a",
                "action": "press",
                "modifiers": ["ctrl"],
                "key_type": "char",
            },
        )
    )

    # Copy (Ctrl+C)
    records.append(
        RawRecord(
            timestamp=copy_time + timedelta(seconds=0.2),
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": "c",
                "action": "press",
                "modifiers": ["ctrl"],
                "key_type": "char",
            },
        )
    )

    # Mouse click at new position
    records.append(
        RawRecord(
            timestamp=copy_time + timedelta(seconds=0.5),
            type=RecordType.MOUSE_RECORD,
            data={"action": "press", "button": "left", "position": [300, 400]},
        )
    )

    records.append(
        RawRecord(
            timestamp=copy_time + timedelta(seconds=0.6),
            type=RecordType.MOUSE_RECORD,
            data={"action": "release", "button": "left", "position": [300, 400]},
        )
    )

    # Paste (Ctrl+V)
    records.append(
        RawRecord(
            timestamp=copy_time + timedelta(seconds=0.8),
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": "v",
                "action": "press",
                "modifiers": ["ctrl"],
                "key_type": "char",
            },
        )
    )

    # Scene 3: Web browsing activity
    print("   🌐 Creating scene 3: Web browsing activity")
    browse_time = base_time + timedelta(seconds=20)

    # Mouse scrolling
    for i in range(5):
        records.append(
            RawRecord(
                timestamp=browse_time + timedelta(seconds=i * 0.3),
                type=RecordType.MOUSE_RECORD,
                data={
                    "action": "scroll",
                    "button": "middle",
                    "position": [500, 300],
                    "delta": [0, -50],
                },
            )
        )

    # Click link
    records.append(
        RawRecord(
            timestamp=browse_time + timedelta(seconds=2),
            type=RecordType.MOUSE_RECORD,
            data={"action": "press", "button": "left", "position": [400, 200]},
        )
    )

    records.append(
        RawRecord(
            timestamp=browse_time + timedelta(seconds=2.1),
            type=RecordType.MOUSE_RECORD,
            data={"action": "release", "button": "left", "position": [400, 200]},
        )
    )

    # 添加截图
    records.append(
        RawRecord(
            timestamp=browse_time + timedelta(seconds=3),
            type=RecordType.SCREENSHOT_RECORD,
            data={
                "action": "capture",
                "width": 1920,
                "height": 1080,
                "format": "JPEG",
                "size_bytes": 300000,
                "file_path": f"/tmp/screenshot_{len(records)}.jpg",
            },
        )
    )

    # Scene 4: Code editing activity
    print("   💻 Creating scene 4: Code editing activity")
    code_time = base_time + timedelta(seconds=30)

    # Input code
    code_lines = ["def hello_world():", "    print('Hello, World!')", "    return True"]

    for line_num, line in enumerate(code_lines):
        for char_num, char in enumerate(line):
            records.append(
                RawRecord(
                    timestamp=code_time
                    + timedelta(seconds=line_num * 2 + char_num * 0.05),
                    type=RecordType.KEYBOARD_RECORD,
                    data={
                        "key": char,
                        "action": "press",
                        "modifiers": [],
                        "key_type": "char",
                    },
                )
            )

        # Press enter after each line
        records.append(
            RawRecord(
                timestamp=code_time
                + timedelta(seconds=line_num * 2 + len(line) * 0.05 + 0.1),
                type=RecordType.KEYBOARD_RECORD,
                data={
                    "key": "enter",
                    "action": "press",
                    "modifiers": [],
                    "key_type": "special",
                },
            )
        )

    # 保存文件 (Ctrl+S)
    records.append(
        RawRecord(
            timestamp=code_time + timedelta(seconds=8),
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": "s",
                "action": "press",
                "modifiers": ["ctrl"],
                "key_type": "char",
            },
        )
    )

    # 添加截图
    records.append(
        RawRecord(
            timestamp=code_time + timedelta(seconds=9),
            type=RecordType.SCREENSHOT_RECORD,
            data={
                "action": "capture",
                "width": 1920,
                "height": 1080,
                "format": "JPEG",
                "size_bytes": 280000,
                "file_path": f"/tmp/screenshot_{len(records)}.jpg",
            },
        )
    )

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
