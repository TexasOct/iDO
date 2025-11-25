#!/usr/bin/env python3
"""
Debug script to check todo time range data in database and API response

This script helps diagnose issues with scheduledEndTime display
"""

import json
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path.home() / ".config" / "ido" / "ido.db"


def check_database():
    """Check raw database data"""
    print("=" * 80)
    print("📊 DATABASE INSPECTION")
    print("=" * 80)

    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check combined_todos with schedule
    cursor.execute("""
        SELECT
            id, title,
            scheduled_date, scheduled_time, scheduled_end_time,
            recurrence_rule, keywords
        FROM combined_todos
        WHERE scheduled_date IS NOT NULL
        AND deleted = 0
        ORDER BY scheduled_date
    """)

    rows = cursor.fetchall()

    if not rows:
        print("ℹ️  No scheduled todos found in combined_todos")
    else:
        print(f"\n📋 Found {len(rows)} scheduled todo(s) in combined_todos:\n")

        for i, row in enumerate(rows, 1):
            print(f"Todo #{i}")
            print(f"  ID: {row['id']}")
            print(f"  Title: {row['title']}")
            print(f"  📅 Scheduled Date: {row['scheduled_date']}")
            print(f"  ⏰ Scheduled Time: {row['scheduled_time']}")
            print(f"  ⏱️  Scheduled End Time: {row['scheduled_end_time']}")
            print(f"  🔄 Recurrence Rule: {row['recurrence_rule']}")

            # Parse keywords
            keywords = json.loads(row['keywords']) if row['keywords'] else []
            print(f"  🏷️  Keywords: {', '.join(keywords)}")

            # Check for anomalies
            if row['scheduled_time'] and row['scheduled_end_time']:
                start_time = row['scheduled_time']
                end_time = row['scheduled_end_time']

                # Parse time (HH:MM)
                start_parts = start_time.split(':')
                end_parts = end_time.split(':')

                if len(start_parts) == 2 and len(end_parts) == 2:
                    start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                    end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

                    if end_minutes < start_minutes:
                        print(f"  ⚠️  WARNING: End time ({end_time}) is before start time ({start_time})!")
                    else:
                        duration_minutes = end_minutes - start_minutes
                        hours = duration_minutes // 60
                        minutes = duration_minutes % 60
                        duration_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                        print(f"  ✅ Duration: {duration_text}")

            print()

    # Check todos table as well
    cursor.execute("""
        SELECT
            id, title,
            scheduled_date, scheduled_time, scheduled_end_time,
            recurrence_rule
        FROM todos
        WHERE scheduled_date IS NOT NULL
        AND deleted = 0
        ORDER BY scheduled_date
    """)

    rows = cursor.fetchall()

    if rows:
        print(f"\n📋 Found {len(rows)} scheduled todo(s) in todos table:\n")
        for i, row in enumerate(rows, 1):
            print(f"Todo #{i}")
            print(f"  ID: {row['id']}")
            print(f"  Title: {row['title']}")
            print(f"  📅 Scheduled Date: {row['scheduled_date']}")
            print(f"  ⏰ Scheduled Time: {row['scheduled_time']}")
            print(f"  ⏱️  Scheduled End Time: {row['scheduled_end_time']}")
            print()

    conn.close()

    print("\n" + "=" * 80)
    print("✅ Database inspection complete")
    print("=" * 80)


def check_table_structure():
    """Check table structure"""
    print("\n" + "=" * 80)
    print("🔧 TABLE STRUCTURE")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for table in ["todos", "combined_todos"]:
        print(f"\n📊 Table: {table}")
        print("-" * 40)

        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        schedule_columns = [
            col for col in columns
            if 'schedule' in col[1].lower() or 'recurrence' in col[1].lower()
        ]

        if schedule_columns:
            print("Schedule-related columns:")
            for col in schedule_columns:
                col_id, name, col_type, not_null, default, pk = col
                print(f"  - {name} ({col_type})")
        else:
            print("  ⚠️  No schedule-related columns found!")

    conn.close()


if __name__ == "__main__":
    print("\n🔍 TODO TIME RANGE DEBUGGING TOOL\n")
    check_database()
    check_table_structure()

    print("\n" + "=" * 80)
    print("💡 NEXT STEPS:")
    print("=" * 80)
    print("""
1. If database shows correct times but frontend shows wrong times:
   - Check browser console for API response
   - Clear any cached data (localStorage)
   - Restart the application

2. If database shows wrong times:
   - The issue is in the save logic
   - Check TodosDetailDialog handleSaveSchedule function

3. If you see "End time is before start time" warning:
   - Data in database is corrupted
   - You can manually fix it with SQL UPDATE
    """)
