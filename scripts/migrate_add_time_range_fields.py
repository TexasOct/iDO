#!/usr/bin/env python3
"""
Database migration script: Add time range fields to todos tables

This script:
1. Adds the scheduled_end_time column to todos and combined_todos tables
2. Adds the recurrence_rule column to todos and combined_todos tables
3. Creates indexes on the new columns for better query performance

Run with: uv run python scripts/migrate_add_time_range_fields.py
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# Database path
DB_PATH = Path.home() / ".config" / "ido" / "ido.db"

def check_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table"""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def migrate():
    """Run migration"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return False

    print(f"📊 Starting migration for database: {DB_PATH}")
    print(f"⏰ Migration time: {datetime.now().isoformat()}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        tables = ["todos", "combined_todos"]

        for table in tables:
            print(f"\n{'='*60}")
            print(f"Migrating table: {table}")
            print(f"{'='*60}\n")

            # Step 1: Add scheduled_end_time column
            if check_column_exists(conn, table, "scheduled_end_time"):
                print(f"✅ Column 'scheduled_end_time' already exists in {table} table")
            else:
                print(f"➕ Adding 'scheduled_end_time' column to {table} table...")
                conn.execute(f"""
                    ALTER TABLE {table}
                    ADD COLUMN scheduled_end_time TEXT
                """)
                conn.commit()
                print("✅ Column added successfully")

            # Step 2: Add recurrence_rule column
            if check_column_exists(conn, table, "recurrence_rule"):
                print(f"✅ Column 'recurrence_rule' already exists in {table} table")
            else:
                print(f"➕ Adding 'recurrence_rule' column to {table} table...")
                conn.execute(f"""
                    ALTER TABLE {table}
                    ADD COLUMN recurrence_rule TEXT
                """)
                conn.commit()
                print("✅ Column added successfully")

        # Step 3: Create indexes for better performance
        print(f"\n{'='*60}")
        print("Creating indexes")
        print(f"{'='*60}\n")

        for table in tables:
            # Index on scheduled_end_time
            print(f"📇 Creating index on {table}.scheduled_end_time...")
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table}_scheduled_end_time
                ON {table}(scheduled_end_time)
            """)

            # Index on recurrence_rule (for quickly finding recurring todos)
            print(f"📇 Creating index on {table}.recurrence_rule...")
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table}_recurrence_rule
                ON {table}(recurrence_rule)
            """)

        conn.commit()
        print("✅ All indexes created successfully")

        # Step 4: Show summary statistics
        print(f"\n{'='*60}")
        print("Migration Summary")
        print(f"{'='*60}\n")

        for table in tables:
            cursor = conn.execute(f"""
                SELECT COUNT(*) as total
                FROM {table}
                WHERE deleted = 0
            """)
            total = cursor.fetchone()["total"]

            cursor = conn.execute(f"""
                SELECT COUNT(*) as with_schedule
                FROM {table}
                WHERE deleted = 0 AND scheduled_date IS NOT NULL
            """)
            with_schedule = cursor.fetchone()["with_schedule"]

            print(f"{table}:")
            print(f"  Total records: {total}")
            print(f"  Scheduled records: {with_schedule}")
            print(f"  Ready for time range and recurrence features ✅\n")

        print("✅ Migration completed successfully!\n")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate()
    exit(0 if success else 1)
