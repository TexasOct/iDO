#!/usr/bin/env python3
"""
Check if activities with empty source_events exist in database
"""

import sys
import os
import json

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_db


def check_empty_activities():
    """Check if there are empty source_events"""
    print("🔍 Checking activities in database...")
    print("=" * 60)

    db = get_db()

    # Query all activities
    activities = db.execute_query(
        "SELECT id, description, start_time, source_events FROM activities ORDER BY start_time DESC LIMIT 100"
    )

    empty_count = 0
    null_count = 0
    valid_count = 0

    for activity in activities:
        source_events = activity.get("source_events")

        if source_events is None:
            null_count += 1
            print(
                f"❌ NULL source_events: {activity['id'][:8]}... - {activity['description'][:50]}"
            )
        elif source_events == "":
            empty_count += 1
            print(
                f"❌ EMPTY source_events: {activity['id'][:8]}... - {activity['description'][:50]}"
            )
        else:
            try:
                events = (
                    json.loads(source_events)
                    if isinstance(source_events, str)
                    else source_events
                )
                if len(events) == 0:
                    empty_count += 1
                    print(
                        f"❌ ZERO events: {activity['id'][:8]}... - {activity['description'][:50]}"
                    )
                else:
                    valid_count += 1
            except Exception as e:
                print(f"⚠️  JSON parse error: {activity['id'][:8]}... - {e}")

    print("\n" + "=" * 60)
    print(f"📊 Statistics:")
    print(f"  ✓ Valid activities: {valid_count}")
    print(f"  ✗ Empty arrays: {empty_count}")
    print(f"  ✗ NULL: {null_count}")
    print(f"  Total: {len(activities)}")

    if empty_count > 0 or null_count > 0:
        print(f"\n⚠️  Found {empty_count + null_count} activities without event data!")
        print("This is why the frontend shows 'No event summary'.")
        return False
    else:
        print("\n✅ All activities have event data")
        return True


if __name__ == "__main__":
    check_empty_activities()
