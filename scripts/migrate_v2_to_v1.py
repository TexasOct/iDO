#!/usr/bin/env python3
"""
Database migration script: Rename v2 tables to v1 names

This script:
1. Drops old v1 tables (events, activities)
2. Renames v2 tables to v1 names (events_v2 -> events, activities_v2 -> activities)
3. Recreates indexes with v1 names
"""

import sqlite3
import sys
from pathlib import Path


def migrate_database(db_path: str) -> None:
    """
    Migrate database from v2 to v1 table names

    Args:
        db_path: Path to SQLite database file
    """
    print(f"Starting migration for database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Backup first
        print("\n[1/6] Creating backup...")
        backup_path = f"{db_path}.backup"
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        print(f"✅ Backup created at: {backup_path}")

        # Check if v2 tables exist
        print("\n[2/6] Checking v2 tables...")
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('events_v2', 'activities_v2')
            """
        )
        v2_tables = [row[0] for row in cursor.fetchall()]

        if not v2_tables:
            print("❌ No v2 tables found. Migration not needed.")
            return

        print(f"✅ Found v2 tables: {', '.join(v2_tables)}")

        # Drop old v1 tables if they exist
        print("\n[3/6] Dropping old v1 tables...")
        cursor.execute("DROP TABLE IF EXISTS events")
        cursor.execute("DROP TABLE IF EXISTS activities")
        conn.commit()
        print("✅ Old v1 tables dropped")

        # Drop old v1 indexes
        print("\n[4/6] Dropping old v1 indexes...")
        old_indexes = [
            "idx_events_timestamp",
            "idx_events_created",
        ]
        for idx in old_indexes:
            cursor.execute(f"DROP INDEX IF EXISTS {idx}")
        conn.commit()
        print("✅ Old v1 indexes dropped")

        # Rename v2 tables to v1 names
        print("\n[5/6] Renaming v2 tables to v1 names...")
        if "events_v2" in v2_tables:
            cursor.execute("ALTER TABLE events_v2 RENAME TO events")
            print("✅ events_v2 -> events")

        if "activities_v2" in v2_tables:
            cursor.execute("ALTER TABLE activities_v2 RENAME TO activities")
            print("✅ activities_v2 -> activities")

        conn.commit()

        # Drop old v2 indexes and create new v1 indexes
        print("\n[6/6] Updating indexes...")

        # Drop old v2 indexes
        old_v2_indexes = [
            "idx_events_v2_start_time",
            "idx_events_v2_created",
            "idx_events_v2_aggregated",
            "idx_activities_v2_start_time",
            "idx_activities_v2_created",
            "idx_activities_v2_updated",
        ]
        for idx in old_v2_indexes:
            cursor.execute(f"DROP INDEX IF EXISTS {idx}")

        # Create new indexes with v1 names
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_start_time
            ON events(start_time DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_created
            ON events(created_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_aggregated
            ON events(aggregated_into_activity_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activities_start_time
            ON activities(start_time DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activities_created
            ON activities(created_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activities_updated
            ON activities(updated_at DESC)
            """
        )

        conn.commit()
        print("✅ Indexes updated")

        # Verify migration
        print("\n[Verification] Checking tables...")
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('events', 'activities', 'events_v2', 'activities_v2')
            ORDER BY name
            """
        )
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Current tables: {', '.join(tables)}")

        if "events" in tables and "activities" in tables:
            if "events_v2" not in tables and "activities_v2" not in tables:
                print("\n✅ Migration completed successfully!")
            else:
                print(
                    "\n⚠️ Migration completed but v2 tables still exist (should not happen)"
                )
        else:
            print("\n❌ Migration failed - v1 tables not found")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Default path
        db_path = str(Path.home() / ".config" / "ido" / "ido.db")

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    print("=" * 60)
    print("Database Migration: v2 tables -> v1 names")
    print("=" * 60)

    try:
        migrate_database(db_path)
        print("\n" + "=" * 60)
        print("Migration completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
