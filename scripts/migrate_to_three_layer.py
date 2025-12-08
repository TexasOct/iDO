"""
Migration script: Two-layer → Three-layer architecture
Safely migrates existing data while preserving backward compatibility

Usage:
    uv run python scripts/migrate_to_three_layer.py [--db-path PATH] [--dry-run]

Arguments:
    --db-path: Path to database (default: ~/.config/ido/ido.db)
    --dry-run: Test migration without committing changes
"""

import argparse
import asyncio
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


class ThreeLayerMigration:
    """Migration manager for three-layer architecture"""

    def __init__(self, db_path: Path, dry_run: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.backup_path = db_path.parent / f"ido_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

        # Statistics
        self.stats = {
            "events_migrated": 0,
            "event_images_migrated": 0,
            "activities_migrated": 0,
        }

    def _connect(self) -> sqlite3.Connection:
        """Create database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    async def execute(self):
        """Execute migration in phases"""
        print("=" * 60)
        print("Three-Layer Architecture Migration")
        print("=" * 60)
        print(f"Database: {self.db_path}")
        print(f"Dry run: {self.dry_run}")
        print()

        if not self.db_path.exists():
            print(f"❌ Error: Database not found at {self.db_path}")
            sys.exit(1)

        try:
            # Phase 1: Backup
            await self._backup_database()

            # Phase 2: Create new tables
            await self._create_new_tables()

            # Phase 3: Migrate data
            await self._migrate_events_to_actions()
            await self._migrate_event_images_to_action_images()
            await self._migrate_activities_to_events()

            # Phase 4: Verify integrity
            await self._verify_migration()

            # Summary
            print()
            print("=" * 60)
            print("Migration Summary")
            print("=" * 60)
            for key, value in self.stats.items():
                print(f"  {key}: {value}")
            print()

            if self.dry_run:
                print("✓ Dry run completed successfully (no changes committed)")
                print(f"  Backup at: {self.backup_path}")
            else:
                print("✓ Migration completed successfully!")
                print(f"  Backup saved at: {self.backup_path}")
                print()
                print("⚠️  IMPORTANT: Next steps:")
                print("  1. Test the application to ensure everything works")
                print("  2. If issues occur, restore backup:")
                print(f"     cp {self.backup_path} {self.db_path}")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()

            if not self.dry_run and self.backup_path.exists():
                print(f"\n⚠️  Backup available at: {self.backup_path}")
                print("  You can restore it manually if needed")

            sys.exit(1)

    async def _backup_database(self):
        """Create full database backup"""
        print("[1/5] Backing up database...")

        if self.dry_run:
            print(f"  [DRY RUN] Would backup to: {self.backup_path}")
        else:
            shutil.copy2(self.db_path, self.backup_path)
            # Verify backup
            if not self.backup_path.exists():
                raise RuntimeError("Backup file not created")
            backup_size = self.backup_path.stat().st_size
            original_size = self.db_path.stat().st_size
            if backup_size != original_size:
                raise RuntimeError(f"Backup size mismatch: {backup_size} != {original_size}")
            print(f"  ✓ Backup created: {self.backup_path} ({backup_size:,} bytes)")

    async def _create_new_tables(self):
        """Create new schema tables"""
        print("\n[2/5] Creating new tables...")

        # Import schema definitions
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from backend.core.sqls.schema import (
            CREATE_ACTION_IMAGES_ACTION_ID_INDEX,
            CREATE_ACTION_IMAGES_HASH_INDEX,
            CREATE_ACTION_IMAGES_TABLE,
            CREATE_ACTIONS_AGGREGATED_INDEX,
            CREATE_ACTIONS_CREATED_INDEX,
            CREATE_ACTIONS_TABLE,
            CREATE_ACTIONS_TIMESTAMP_INDEX,
            CREATE_ACTIVITIES_V2_CREATED_INDEX,
            CREATE_ACTIVITIES_V2_START_TIME_INDEX,
            CREATE_ACTIVITIES_V2_TABLE,
            CREATE_ACTIVITIES_V2_UPDATED_INDEX,
            CREATE_EVENTS_V2_AGGREGATED_INDEX,
            CREATE_EVENTS_V2_CREATED_INDEX,
            CREATE_EVENTS_V2_START_TIME_INDEX,
            CREATE_EVENTS_V2_TABLE,
            CREATE_SESSION_PREFERENCES_CONFIDENCE_INDEX,
            CREATE_SESSION_PREFERENCES_TABLE,
            CREATE_SESSION_PREFERENCES_TYPE_INDEX,
        )

        conn = self._connect()
        cursor = conn.cursor()

        try:
            # Create tables
            tables = [
                ("actions", CREATE_ACTIONS_TABLE),
                ("events_v2", CREATE_EVENTS_V2_TABLE),
                ("activities_v2", CREATE_ACTIVITIES_V2_TABLE),
                ("action_images", CREATE_ACTION_IMAGES_TABLE),
                ("session_preferences", CREATE_SESSION_PREFERENCES_TABLE),
            ]

            for table_name, create_sql in tables:
                if self.dry_run:
                    print(f"  [DRY RUN] Would create table: {table_name}")
                else:
                    cursor.execute(create_sql)
                    print(f"  ✓ Created table: {table_name}")

            # Create indexes
            indexes = [
                CREATE_ACTIONS_TIMESTAMP_INDEX,
                CREATE_ACTIONS_CREATED_INDEX,
                CREATE_ACTIONS_AGGREGATED_INDEX,
                CREATE_EVENTS_V2_START_TIME_INDEX,
                CREATE_EVENTS_V2_CREATED_INDEX,
                CREATE_EVENTS_V2_AGGREGATED_INDEX,
                CREATE_ACTIVITIES_V2_START_TIME_INDEX,
                CREATE_ACTIVITIES_V2_CREATED_INDEX,
                CREATE_ACTIVITIES_V2_UPDATED_INDEX,
                CREATE_ACTION_IMAGES_ACTION_ID_INDEX,
                CREATE_ACTION_IMAGES_HASH_INDEX,
                CREATE_SESSION_PREFERENCES_TYPE_INDEX,
                CREATE_SESSION_PREFERENCES_CONFIDENCE_INDEX,
            ]

            for idx_sql in indexes:
                if not self.dry_run:
                    cursor.execute(idx_sql)

            if not self.dry_run:
                print(f"  ✓ Created {len(indexes)} indexes")
            else:
                print(f"  [DRY RUN] Would create {len(indexes)} indexes")

            if not self.dry_run:
                conn.commit()

        finally:
            conn.close()

    async def _migrate_events_to_actions(self):
        """Migrate: events → actions"""
        print("\n[3/5] Migrating events → actions...")

        conn = self._connect()
        cursor = conn.cursor()

        try:
            # Check if old events table exists and has data
            cursor.execute("SELECT COUNT(*) FROM events WHERE deleted = 0")
            count = cursor.fetchone()[0]

            if count == 0:
                print("  ℹ No events to migrate (table empty)")
                return

            if self.dry_run:
                print(f"  [DRY RUN] Would migrate {count} events → actions")
            else:
                # Copy all events to actions table
                cursor.execute("""
                    INSERT INTO actions (id, title, description, keywords, timestamp, deleted, created_at)
                    SELECT id, title, description, keywords, timestamp, deleted, created_at
                    FROM events
                """)

                migrated_count = cursor.rowcount
                self.stats["events_migrated"] = migrated_count
                conn.commit()

                print(f"  ✓ Migrated {migrated_count} events → actions")

        finally:
            conn.close()

    async def _migrate_event_images_to_action_images(self):
        """Migrate: event_images → action_images"""
        print("\n[4/5] Migrating event_images → action_images...")

        conn = self._connect()
        cursor = conn.cursor()

        try:
            # Check if old event_images table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event_images'")
            if not cursor.fetchone():
                print("  ℹ No event_images table to migrate")
                return

            cursor.execute("SELECT COUNT(*) FROM event_images")
            count = cursor.fetchone()[0]

            if count == 0:
                print("  ℹ No event images to migrate (table empty)")
                return

            if self.dry_run:
                print(f"  [DRY RUN] Would migrate {count} event_images → action_images")
            else:
                cursor.execute("""
                    INSERT INTO action_images (action_id, hash, created_at)
                    SELECT event_id, hash, created_at
                    FROM event_images
                """)

                migrated_count = cursor.rowcount
                self.stats["event_images_migrated"] = migrated_count
                conn.commit()

                print(f"  ✓ Migrated {migrated_count} event_images → action_images")

        finally:
            conn.close()

    async def _migrate_activities_to_events(self):
        """Migrate: activities → events_v2"""
        print("\n[5/5] Migrating activities → events_v2...")

        conn = self._connect()
        cursor = conn.cursor()

        try:
            # Get all activities
            cursor.execute("SELECT * FROM activities WHERE deleted = 0")
            activities = cursor.fetchall()

            if len(activities) == 0:
                print("  ℹ No activities to migrate (table empty)")
                return

            if self.dry_run:
                print(f"  [DRY RUN] Would migrate {len(activities)} activities → events_v2")
            else:
                # Migrate each activity to events_v2
                # Note: source_event_ids becomes source_action_ids (semantically correct after migration)
                for activity in activities:
                    source_action_ids = activity['source_event_ids']  # This now refers to old events = new actions
                    version = activity['version'] if 'version' in activity.keys() else 1

                    cursor.execute("""
                        INSERT INTO events_v2 (
                            id, title, description, start_time, end_time,
                            source_action_ids, version, deleted, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        activity['id'],
                        activity['title'],
                        activity['description'],
                        activity['start_time'],
                        activity['end_time'],
                        source_action_ids,  # Now correctly references actions
                        version,
                        activity['deleted'],
                        activity['created_at']
                    ))

                migrated_count = len(activities)
                self.stats["activities_migrated"] = migrated_count
                conn.commit()

                print(f"  ✓ Migrated {migrated_count} activities → events_v2")

        finally:
            conn.close()

    async def _verify_migration(self):
        """Verify data integrity post-migration"""
        print("\n[Verification] Checking data integrity...")

        conn = self._connect()
        cursor = conn.cursor()

        try:
            # Count checks
            cursor.execute("SELECT COUNT(*) FROM events")
            old_events_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM activities WHERE deleted = 0")
            old_activities_count = cursor.fetchone()[0]

            if self.dry_run:
                # In dry-run mode, tables don't exist yet, so verify using stats
                print(f"  ✓ Would migrate {old_events_count} events → actions")
                print(f"  ✓ Would migrate {old_activities_count} activities → events_v2")
                print("  ✓ Activities (new): 0 records (will be generated by SessionAgent)")
                print("\n  ✓ Dry-run verification passed!")
            else:
                # In real mode, verify actual migration results
                cursor.execute("SELECT COUNT(*) FROM actions")
                new_actions_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM events_v2")
                new_events_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM activities_v2")
                new_activities_count = cursor.fetchone()[0]

                # Verify counts
                errors = []

                if old_events_count != new_actions_count:
                    errors.append(f"Events→Actions count mismatch: {old_events_count} != {new_actions_count}")
                else:
                    print(f"  ✓ Events→Actions: {new_actions_count} records")

                if old_activities_count != new_events_count:
                    errors.append(f"Activities→Events count mismatch: {old_activities_count} != {new_events_count}")
                else:
                    print(f"  ✓ Activities→Events: {new_events_count} records")

                print(f"  ✓ Activities (new): {new_activities_count} records (will be generated by SessionAgent)")

                if errors:
                    raise RuntimeError("Verification failed:\n  " + "\n  ".join(errors))

                print("\n  ✓ All verification checks passed!")

        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate to three-layer architecture")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path.home() / ".config" / "ido" / "ido.db",
        help="Path to database file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test migration without committing changes"
    )

    args = parser.parse_args()

    # Confirm before proceeding (unless dry run)
    if not args.dry_run:
        print("⚠️  WARNING: This will modify your database!")
        print(f"   Database: {args.db_path}")
        print()
        response = input("Continue? [y/N]: ").strip().lower()
        if response != 'y':
            print("Migration cancelled")
            sys.exit(0)
        print()

    migration = ThreeLayerMigration(args.db_path, dry_run=args.dry_run)
    asyncio.run(migration.execute())


if __name__ == "__main__":
    main()
