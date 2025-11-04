#!/usr/bin/env python3
"""
Test activity processing logic
Specifically test the new functionality of sequential traversal of events and individual merge judgment
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.pipeline import ProcessingPipeline
from core.models import RawRecord, Event, RecordType
from core.logger import get_logger

logger = get_logger(__name__)


async def test_activity_processing():
    """Test activity processing logic"""
    print("🧪 Testing activity processing logic")
    print("=" * 60)

    # Create processing pipeline
    pipeline = ProcessingPipeline()
    await pipeline.start()

    try:
        # Create mock events
        events = []

        # Event 1: Code editing
        event1 = Event(
            id="event-1",
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now() - timedelta(minutes=4),
            type=RecordType.KEYBOARD_RECORD,
            summary="User is writing a Python function in the code editor",
            source_data=[],
        )
        events.append(event1)

        # Event 2: Continue code editing (should merge)
        event2 = Event(
            id="event-2",
            start_time=datetime.now() - timedelta(minutes=4),
            end_time=datetime.now() - timedelta(minutes=3),
            type=RecordType.KEYBOARD_RECORD,
            summary="User continues writing other parts of the same Python function",
            source_data=[],
        )
        events.append(event2)

        # Event 3: Run tests (may not merge)
        event3 = Event(
            id="event-3",
            start_time=datetime.now() - timedelta(minutes=3),
            end_time=datetime.now() - timedelta(minutes=2),
            type=RecordType.KEYBOARD_RECORD,
            summary="User runs test commands in the terminal",
            source_data=[],
        )
        events.append(event3)

        # Event 4: View results (may merge with test)
        event4 = Event(
            id="event-4",
            start_time=datetime.now() - timedelta(minutes=2),
            end_time=datetime.now() - timedelta(minutes=1),
            type=RecordType.MOUSE_RECORD,
            summary="User views test run results",
            source_data=[],
        )
        events.append(event4)

        print(f"📝 Created {len(events)} test events")
        for i, event in enumerate(events, 1):
            print(f"   {i}. {event.summary}")

        print(f"\n🔄 Starting activity processing...")
        print("=" * 60)

        # Process events
        result = await pipeline._process_activities(events)

        print(f"\n📊 Processing results:")
        print(f"   - Generated activities: {len(result['activities'])}")
        print(f"   - Merged: {result['merged']}")
        print(f"   - Current activity: {'Yes' if pipeline.current_activity else 'No'}")

        # Display generated activities
        if result["activities"]:
            print(f"\n📋 Generated activities:")
            for i, activity in enumerate(result["activities"], 1):
                print(f"   {i}. {activity['description']}")
                print(
                    f"      Time: {activity['start_time'].strftime('%H:%M:%S')} - {activity['end_time'].strftime('%H:%M:%S')}"
                )
                print(f"      Event count: {activity['event_count']}")

        # Display current activity
        if pipeline.current_activity:
            print(f"\n🎯 Current activity:")
            print(f"   - Description: {pipeline.current_activity['description']}")
            print(
                f"   - Time: {pipeline.current_activity['start_time'].strftime('%H:%M:%S')} - {pipeline.current_activity['end_time'].strftime('%H:%M:%S')}"
            )
            print(f"   - Event count: {pipeline.current_activity['event_count']}")

        print(f"\n✅ Activity processing test completed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await pipeline.stop()


if __name__ == "__main__":
    print("🧪 Activity Processing Logic Test")
    print(
        "This test will verify the new functionality of sequential traversal of events and individual merge judgment"
    )
    print()

    try:
        asyncio.run(test_activity_processing())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)
