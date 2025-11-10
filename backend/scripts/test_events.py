#!/usr/bin/env python3
"""
Real monitoring test script - Event aggregation version
Actually monitors user's keyboard, mouse and screenshot operations, then aggregates into events and outputs
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.manager import PerceptionManager
from processing.pipeline import ProcessingPipeline
from core.logger import get_logger

logger = get_logger(__name__)


async def test_events_capture():
    """Real monitoring test - Listen for 50 seconds and aggregate into events"""
    print("🎯 iDO Event Aggregation Test")
    print("=" * 60)
    print("This test will actually monitor your keyboard, mouse and screen operations")
    print("Then aggregate into events and output")
    print(
        "📸 Screenshots will be automatically saved to backend/tmp/screenshots/ folder"
    )
    print("Please perform some operations within these 50 seconds, such as:")
    print("  - Typing, using shortcuts")
    print("  - Moving mouse, clicking, scrolling")
    print("  - Switching windows, browsing web")
    print("=" * 60)

    # Create perception manager
    perception_manager = PerceptionManager(
        capture_interval=0.1,  # Screenshot every 0.1 seconds for higher precision
        window_size=50,        # 50-second sliding window to ensure covering the entire listening time
        on_data_captured=None  # No real-time output, process all at once at the end
    )

    # Create processing pipeline
    processing_pipeline = ProcessingPipeline()

    try:
        # Start perception manager
        print("📡 Starting perception manager...")
        await perception_manager.start()
        print("✅ Perception manager started!")

        # Start processing pipeline
        print("🔄 Starting processing pipeline...")
        await processing_pipeline.start()
        print("✅ Processing pipeline started!")

        print(f"\n⏱️  Starting listening, lasting 50 seconds...")
        print("=" * 60)

        # Listen for 50 seconds
        for i in range(50):
            await asyncio.sleep(1)
            print(f"⏰ Listening... {i+1}/50 seconds")

        print(f"\n⏹️  Listening ended!")
        print("=" * 60)

        # Get all captured records
        all_records = perception_manager.get_recent_records(1000)  # Get the most recent 1000 records
        print(f"📋 Total captured records: {len(all_records)}")

        if not all_records:
            print("❌ No records captured, please ensure you have permission to access input devices")
            return

        # Sort all records by timestamp
        all_records.sort(key=lambda x: x.timestamp)

        # Display raw record statistics
        print(f"\n📊 Raw record statistics:")
        print("=" * 60)
        keyboard_count = sum(
            1 for r in all_records if r.type.value == "keyboard_record"
        )
        mouse_count = sum(1 for r in all_records if r.type.value == "mouse_record")
        screenshot_count = sum(
            1 for r in all_records if r.type.value == "screenshot_record"
        )

        print(f"   - Total records: {len(all_records)}")
        print(f"   - Keyboard records: {keyboard_count}")
        print(f"   - Mouse records: {mouse_count}")
        print(f"   - Screenshot records: {screenshot_count}")

        if all_records:
            start_time = all_records[0].timestamp
            end_time = all_records[-1].timestamp
            duration = (end_time - start_time).total_seconds()
            print(f"   - Time range: {start_time.strftime('%H:%M:%S.%f')[:-3]} - {end_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"   - Actual duration: {duration:.2f} seconds")

        # Process raw records, aggregate into events
        print(f"\n🔄 Starting to aggregate events...")
        print("=" * 60)

        # Process all records at once to avoid state confusion caused by batching
        all_events = []
        all_activities = []
        total_activities = 0

        if all_records:
            # Sort by timestamp
            all_records.sort(key=lambda x: x.timestamp)

            print(f"\n📦 Processing all data ({len(all_records)} records)...")
            start_time = all_records[0].timestamp
            end_time = all_records[-1].timestamp
            print(
                f"   - Time range: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}"
            )

            # Process all records at once
            result = await processing_pipeline.process_raw_records(all_records)

                # Display processing results
                print(f"   ✅ Created {len(result['events'])} events")
                print(f"   ✅ Created {len(result['activities'])} activities")
                print(f"   {'🔄 Merged into existing activity' if result['merged'] else '🆕 Created new activity'}")

            all_events.extend(result["events"])
            total_activities += len(result["activities"])
            all_activities.extend(result["activities"])

        # Force complete current activity
        await processing_pipeline.force_finalize_activity()

        print(f"\n📝 Aggregated Events Details:")
    print("=" * 60)

    if not all_events:
        print("❌ No events generated")
        return

    # Sort events by time
    all_events.sort(key=lambda x: x.start_time)

    for i, event in enumerate(all_events, 1):
        start_time_str = event.start_time.strftime("%H:%M:%S.%f")[:-3]
        end_time_str = event.end_time.strftime("%H:%M:%S.%f")[:-3]
        duration = (event.end_time - event.start_time).total_seconds()

        print(f"{i:2d}. 🎯 Event [{event.id[:8]}...]")
        print(f"     ⏰ Time: {start_time_str} - {end_time_str} ({duration:.2f}s)")
        print(f"     📝 Type: {event.type.value}")
        print(f"     📄 Summary: {event.summary}")
        print(f"     📊 Source data: {len(event.source_data)} records")

            # 显示该事件包含的截图
            event_screenshots = [
                r
                for r in event.source_data
                if r.type.value == "screenshot_record"
                and hasattr(r, "screenshot_path")
                and r.screenshot_path
            ]
            if event_screenshots:
                print(f"     📸 Screenshot files ({len(event_screenshots)} files):")
                for k, screenshot_record in enumerate(event_screenshots, 1):
                    screenshot_time = screenshot_record.timestamp.strftime(
                        "%H:%M:%S.%f"
                    )[:-3]
                    width = screenshot_record.data.get("width", 0)
                    height = screenshot_record.data.get("height", 0)
                    print(
                        f"        {k}. [{screenshot_time}] {width}x{height} -> {screenshot_record.screenshot_path}"
                    )
            else:
                print(f"     📸 Screenshot files: None")

            # Display source data details
            print(f"     📋 Source data details:")
            for j, record in enumerate(event.source_data[:5], 1):  # Only show first 5
                record_time = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
                record_type = record.type.value

                if record_type == "keyboard_record":
                    key = record.data.get("key", "unknown")
                    action = record.data.get("action", "unknown")
                    modifiers = record.data.get("modifiers", [])
                    mod_str = f" +{'+'.join(modifiers)}" if modifiers else ""
                    print(f"        {j}. ⌨️  [{record_time}] {key}{mod_str} ({action})")
                elif record_type == "mouse_record":
                    action = record.data.get("action", "unknown")
                    button = record.data.get("button", "unknown")
                    if "position" in record.data:
                        pos = record.data["position"]
                        print(
                            f"        {j}. 🖱️  [{record_time}] {action} ({button}) at {pos}"
                        )
                    else:
                        print(f"        {j}. 🖱️  [{record_time}] {action} ({button})")
                elif record_type == "screenshot_record":
                    width = record.data.get("width", 0)
                    height = record.data.get("height", 0)
                    screenshot_path = getattr(record, "screenshot_path", None)
                    if screenshot_path:
                        print(
                            f"        {j}. 📸 [{record_time}] {width}x{height} -> {screenshot_path}"
                        )
                    else:
                        print(f"        {j}. 📸 [{record_time}] {width}x{height}")

            if len(event.source_data) > 5:
                print(f"        ... {len(event.source_data) - 5} more records")

            print()  # Empty line separator

        print("--------------------------------")
        print("Aggregated Activities Details:")
        print("=" * 60)

        if all_activities:
            for i, activity in enumerate(all_activities, 1):
                activity_id = activity.get("id", "unknown")
                start_time = activity.get("start_time")
                end_time = activity.get("end_time")
                description = activity.get("description", "Unknown activity")
                event_count = activity.get("event_count", 0)

                # Format time display
                if start_time and end_time:
                    start_str = (
                        start_time.strftime("%H:%M:%S.%f")[:-3]
                        if hasattr(start_time, "strftime")
                        else str(start_time)
                    )
                    end_str = (
                        end_time.strftime("%H:%M:%S.%f")[:-3]
                        if hasattr(end_time, "strftime")
                        else str(end_time)
                    )
                    duration = (
                        (end_time - start_time).total_seconds()
                        if hasattr(end_time, "__sub__")
                        and hasattr(start_time, "__sub__")
                        else 0
                    )
                    duration_str = f"({duration:.2f}s)"
                else:
                    start_str = "Unknown"
                    end_str = "Unknown"
                    duration_str = ""

                print(f"{i:2d}. 🎯 Activity [{activity_id[:8]}...]")
                print(f"     ⏰ Time: {start_str} - {end_str} {duration_str}")
                print(f"     📝 Description: {description}")
                print(f"     📊 Event count: {event_count}")

                # Display source event information
                source_events = activity.get("source_events", [])
                if source_events:
                    print(f"     📋 Source events: {len(source_events)}")
                    # Display brief information of the first 3 source events
                    for j, event in enumerate(source_events[:3], 1):
                        if hasattr(event, "summary"):
                            event_summary = event.summary
                        else:
                            event_summary = (
                                event.get("summary", "No summary")
                                if isinstance(event, dict)
                                else "No summary"
                            )
                        print(
                            f"        {j}. {event_summary[:50]}{'...' if len(str(event_summary)) > 50 else ''}"
                        )

                    if len(source_events) > 3:
                        print(f"        ... {len(source_events) - 3} more events")

                print()  # Empty line separator
        else:
            print("❌ No activities generated")

        print("--------------------------------")

        # Display final statistics
        print(f"\\n📈 Final statistics:")
        print("=" * 60)

        print(f"   - Raw records: {len(all_records)}")
        print(f"   - Generated events: {len(all_events)}")
        print(f"   - Generated activities: {total_activities}")

        # Count screenshot files
        screenshot_records = [
            r for r in all_records if r.type.value == "screenshot_record"
        ]
        screenshot_files = [
            r
            for r in screenshot_records
            if hasattr(r, "screenshot_path") and r.screenshot_path
        ]
        print(f"   - Screenshot records: {len(screenshot_records)}")
        print(f"   - Screenshot files: {len(screenshot_files)}")

        if all_events:
            event_start = all_events[0].start_time
            event_end = all_events[-1].end_time
            total_duration = (event_end - event_start).total_seconds()
            print(
                f"Event time range: {event_start.strftime('%H:%M:%S.%f')[:-3]} - {event_end.strftime('%H:%M:%S.%f')[:-3]}"
            )
            print(f"   - Total event duration: {total_duration:.2f} seconds")

        print(f"\n✅ Event aggregation test completed!")

    except KeyboardInterrupt:
        print("\n⏹️ User interrupted test")
    except Exception as e:
        print(f"\n❌ Error occurred during test: {e}")
        logger.error(f"Test error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Stop managers
        print("\n🛑 Stopping perception manager...")
        await perception_manager.stop()
        print("🛑 Stopping processing pipeline...")
        await processing_pipeline.stop()
        print("✅ Test completed!")


if __name__ == "__main__":
    print("🎯 iDO Event Aggregation Test")
    print("This test will actually monitor your operations and aggregate them into events")
    print("Note: On some systems, you may need permissions to capture input events")
    print()

    try:
        asyncio.run(test_events_capture())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)
