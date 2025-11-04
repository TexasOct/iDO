#!/usr/bin/env python3
"""
Detailed diagnosis of activity data format and integrity
"""

import sys
import os
import json

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_db


def diagnose_activities():
    """Detailed diagnosis of activity data"""
    print("🔍 Detailed diagnosis of activity data...")
    print("=" * 80)

    db = get_db()

    # Query all activities
    activities = db.execute_query(
        "SELECT id, description, start_time, end_time, source_events FROM activities ORDER BY start_time DESC LIMIT 20"
    )

    print(f"\n📊 Total {len(activities)} activities\n")

    for i, activity in enumerate(activities, 1):
        print(f"\n{'=' * 80}")
        print(f"Activity #{i}")
        print(f"{'=' * 80}")
        print(f"ID: {activity['id']}")
        print(f"Description: {activity['description']}")
        print(f"Start time: {activity['start_time']}")
        print(f"End time: {activity['end_time']}")

        source_events = activity.get("source_events")

        if source_events is None:
            print(f"❌ source_events: NULL")
            continue
        elif source_events == "":
            print(f"❌ source_events: EMPTY STRING")
            continue

        try:
            # Try to parse JSON
            events = (
                json.loads(source_events)
                if isinstance(source_events, str)
                else source_events
            )
            event_count = len(events)

            if event_count == 0:
                print(f"❌ source_events: [] (empty array)")
            else:
                print(f"✓ source_events: {event_count} events")

                # Check the format of each event
                for j, event in enumerate(events[:3], 1):  # Only show first 3
                    print(f"\n  Event #{j}:")
                    print(f"    - id: {event.get('id', 'MISSING')}")
                    print(f"    - summary: {event.get('summary', 'MISSING')[:60]}...")
                    print(f"    - start_time: {event.get('start_time', 'MISSING')}")
                    print(f"    - end_time: {event.get('end_time', 'MISSING')}")
                    print(f"    - type: {event.get('type', 'MISSING')}")

                    # Check source_data
                    source_data = event.get("source_data", [])
                    if isinstance(source_data, list):
                        print(f"    - source_data: {len(source_data)} records")

                        # Count types in source_data
                        types = {}
                        for record in source_data:
                            record_type = record.get("type", "unknown")
                            types[record_type] = types.get(record_type, 0) + 1

                        print(f"      Type distribution: {dict(types)}")
                    else:
                        print(f"    - source_data: ❌ Not an array")

                if event_count > 3:
                    print(f"\n  ... {event_count - 3} more events")

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"   Raw data: {source_events[:200]}...")
        except Exception as e:
            print(f"❌ Processing failed: {e}")

    print(f"\n{'=' * 80}")
    print("✅ Diagnosis completed")


if __name__ == "__main__":
    diagnose_activities()
