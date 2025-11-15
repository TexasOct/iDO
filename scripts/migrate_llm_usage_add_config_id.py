#!/usr/bin/env python3
"""
Database migration script: Add model_config_id to llm_token_usage table

This script:
1. Adds the model_config_id column to llm_token_usage table (if not exists)
2. Creates an index on model_config_id
3. Attempts to backfill model_config_id for existing records by matching model names

Run with: uv run python scripts/migrate_llm_usage_add_config_id.py
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
        # Step 1: Check if column already exists
        if check_column_exists(conn, "llm_token_usage", "model_config_id"):
            print("✅ Column 'model_config_id' already exists in llm_token_usage table")
        else:
            print("➕ Adding 'model_config_id' column to llm_token_usage table...")
            conn.execute("""
                ALTER TABLE llm_token_usage
                ADD COLUMN model_config_id TEXT
            """)
            conn.commit()
            print("✅ Column added successfully")

        # Step 2: Create index if not exists
        print("\n📇 Creating index on model_config_id...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_usage_model_config_id
            ON llm_token_usage(model_config_id)
        """)
        conn.commit()
        print("✅ Index created successfully")

        # Step 3: Backfill model_config_id for existing records
        print("\n🔄 Backfilling model_config_id for existing records...")

        # Get count of records without model_config_id
        cursor = conn.execute("""
            SELECT COUNT(*) as count
            FROM llm_token_usage
            WHERE model_config_id IS NULL
        """)
        null_count = cursor.fetchone()["count"]

        if null_count == 0:
            print("✅ All records already have model_config_id set")
        else:
            print(f"📝 Found {null_count} records without model_config_id")

            # Get all model configurations
            models = conn.execute("""
                SELECT id, model, name
                FROM llm_models
                ORDER BY created_at DESC
            """).fetchall()

            updated_count = 0
            for model_config in models:
                config_id = model_config["id"]
                model_name = model_config["model"]
                config_name = model_config["name"]

                # Update records that match this model name
                cursor = conn.execute("""
                    UPDATE llm_token_usage
                    SET model_config_id = ?
                    WHERE model = ? AND model_config_id IS NULL
                """, (config_id, model_name))

                rows_updated = cursor.rowcount
                if rows_updated > 0:
                    updated_count += rows_updated
                    print(f"  ✓ Linked {rows_updated} records to config '{config_name}' (model: {model_name})")

            conn.commit()
            print(f"\n✅ Backfilled {updated_count} records")

            # Check remaining null records
            cursor = conn.execute("""
                SELECT COUNT(*) as count
                FROM llm_token_usage
                WHERE model_config_id IS NULL
            """)
            remaining_null = cursor.fetchone()["count"]

            if remaining_null > 0:
                print(f"⚠️  {remaining_null} records could not be linked (no matching model configuration)")
                print("   These records will use model name for statistics until re-recorded")

        # Step 4: Show summary statistics
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)

        stats = conn.execute("""
            SELECT
                CASE
                    WHEN model_config_id IS NULL THEN 'Without config ID'
                    ELSE 'With config ID'
                END as status,
                COUNT(*) as count,
                SUM(total_tokens) as tokens
            FROM llm_token_usage
            GROUP BY status
        """).fetchall()

        for stat in stats:
            print(f"{stat['status']:20} {stat['count']:8} records  {stat['tokens']:15,} tokens")

        print("\n✅ Migration completed successfully!\n")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate()
    exit(0 if success else 1)
