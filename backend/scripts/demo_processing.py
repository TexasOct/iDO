#!/usr/bin/env python3
"""
Processing module demonstration script
Showcases event filtering, summarization, merging, and persistence functionality
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


async def demo_processing():
    """Demonstrate processing module functionality"""
    print("🔄 Starting iDO Processing demo...")
    print("=" * 50)

    # Create processing pipeline
    pipeline = ProcessingPipeline()

    try:
        # Start pipeline
        print("📡 Starting processing pipeline...")
        await pipeline.start()

        print("✅ Processing pipeline started!")
        print("\n📋 Simulating user interaction data...")
        print("=" * 50)

        # Simulate different types of user interaction data
        test_records = create_test_records()

        print(f"📊 Created {len(test_records)} test records")

        # Process data in batches
        batch_size = 5
        for i in range(0, len(test_records), batch_size):
            batch = test_records[i : i + batch_size]
            print(
                f"\n🔄 Processing batch {i // batch_size + 1} ({len(batch)} records)..."
            )

            # Process records
            result = await pipeline.process_raw_records(batch)

            # Display results
            print(f"   ✅ Created {len(result['events'])} events")
            print(f"   ✅ Created {len(result['activities'])} activities")
            print(
                f"   {'🔄 Merged into existing activity' if result['merged'] else '🆕 Created new activity'}"
            )

            # Display event details
            for event in result["events"]:
                print(f"      📝 Event: {event.type.value} - {event.summary}")

            # Display activity details
            for activity in result["activities"]:
                print(f"      🎯 Activity: {activity['description']}")

        # Display final statistics
        print("\n" + "=" * 50)
        print("📈 Processing completion statistics:")
        stats = pipeline.get_stats()
        print(f"   - Total processed records: {stats['stats']['total_processed']}")
        print(f"   - Created events: {stats['stats']['events_created']}")
        print(f"   - Created activities: {stats['stats']['activities_created']}")
        print(f"   - Merged activities: {stats['stats']['activities_merged']}")

        # Get recent activities
        recent_activities = await pipeline.get_recent_activities(5)
        if recent_activities:
            print(f"\n📋 Recent {len(recent_activities)} activities:")
            for i, activity in enumerate(recent_activities, 1):
                print(f"   {i}. {activity['description']}")
                print(f"      Time: {activity['start_time']} - {activity['end_time']}")
                print(f"      Event count: {activity.get('event_count', 0)}")

        # Get recent events
        recent_events = await pipeline.get_recent_events(10)
        if recent_events:
            print(f"\n📝 Recent {len(recent_events)} events:")
            for i, event in enumerate(recent_events, 1):
                print(f"   {i}. [{event.type.value}] {event.summary}")
                print(f"      Time: {event.start_time} - {event.end_time}")

    except Exception as e:
        print(f"\n❌ Error occurred during demonstration: {e}")
        logger.error(f"Demo error: {e}")
    finally:
        # Stop pipeline
        print("\n🛑 Stopping processing pipeline...")
        await pipeline.stop()
        print("✅ Demo completed!")


def create_test_records():
    """Create test records"""
    base_time = datetime.now()
    records = []

    # Simulate typing activity
    typing_keys = ["h", "e", "l", "l", "o", " ", "w", "o", "r", "l", "d"]
    for i, key in enumerate(typing_keys):
        records.append(
            RawRecord(
                timestamp=base_time + timedelta(seconds=i * 0.5),
                type=RecordType.KEYBOARD_RECORD,
                data={
                    "key": key,
                    "action": "press",
                    "modifiers": [],
                    "key_type": "char",
                },
            )
        )

    # Simulate special key operations
    records.append(
        RawRecord(
            timestamp=base_time + timedelta(seconds=6),
            type=EventType.KEYBOARD_EVENT,
            data={
                "key": "enter",
                "action": "press",
                "modifiers": [],
                "key_type": "special",
            },
        )
    )

    # Simulate mouse operations
    mouse_actions = [
        ("press", "left", (100, 200)),
        ("release", "left", (100, 200)),
        ("press", "left", (150, 250)),
        ("drag", "left", (200, 300)),
        ("drag_end", "left", (250, 350)),
    ]

    for i, (action, button, pos) in enumerate(mouse_actions):
        records.append(
            RawRecord(
                timestamp=base_time + timedelta(seconds=7 + i * 0.3),
                type=RecordType.MOUSE_RECORD,
                data={"action": action, "button": button, "position": pos},
            )
        )

    # Simulate scroll operations
    for i in range(3):
        records.append(
            RawRecord(
                timestamp=base_time + timedelta(seconds=9 + i * 0.1),
                type=RecordType.MOUSE_RECORD,
                data={"action": "scroll", "dx": 0, "dy": 10, "position": (200, 300)},
            )
        )

    # Simulate screenshots
    for i in range(2):
        records.append(
            RawRecord(
                timestamp=base_time + timedelta(seconds=10 + i * 2),
                type=RecordType.SCREENSHOT_RECORD,
                data={
                    "action": "capture",
                    "width": 1920,
                    "height": 1080,
                    "format": "JPEG",
                    "size_bytes": 200000,
                    "hash": f"screenshot_{i}",
                },
            )
        )

    # Simulate combo key operations
    records.append(
        RawRecord(
            timestamp=base_time + timedelta(seconds=15),
            type=EventType.KEYBOARD_EVENT,
            data={
                "key": "c",
                "action": "press",
                "modifiers": ["ctrl"],
                "key_type": "char",
            },
        )
    )

    records.append(
        RawRecord(
            timestamp=base_time + timedelta(seconds=16),
            type=EventType.KEYBOARD_EVENT,
            data={
                "key": "v",
                "action": "press",
                "modifiers": ["ctrl"],
                "key_type": "char",
            },
        )
    )

    # Simulate another activity (web browsing)
    browse_time = base_time + timedelta(seconds=20)
    browse_actions = [
        ("press", "left", (300, 400)),
        ("release", "left", (300, 400)),
        ("scroll", "middle", (300, 400)),
        ("scroll", "middle", (300, 400)),
        ("press", "left", (400, 500)),
        ("release", "left", (400, 500)),
    ]

    for i, (action, button, pos) in enumerate(browse_actions):
        records.append(
            RawRecord(
                timestamp=browse_time + timedelta(seconds=i * 0.5),
                type=RecordType.MOUSE_RECORD,
                data={"action": action, "button": button, "position": pos},
            )
        )

    return records


if __name__ == "__main__":
    print("🎯 iDO Processing Module Demo")
    print(
        "This demo will showcase event filtering, summarization, merging, and persistence features"
    )
    print()

    try:
        asyncio.run(demo_processing())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\\n💥 Demo failed: {e}")
        sys.exit(1)
