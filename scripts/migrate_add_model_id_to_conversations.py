"""
Migration script: Add model_id column to conversations table

This script adds the model_id column to the existing conversations table.
"""

import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    """Get the database file path"""
    import platform

    system = platform.system()
    if system == "Darwin":  # macOS
        config_dir = Path.home() / ".config" / "ido"
    elif system == "Windows":
        config_dir = Path.home() / "AppData" / "Local" / "ido"
    else:  # Linux
        config_dir = Path.home() / ".config" / "ido"

    return config_dir / "ido.db"


def migrate():
    """Run the migration"""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False

    print(f"📂 Found database at {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]

        if "model_id" in columns:
            print("✅ Column 'model_id' already exists in conversations table")
            conn.close()
            return True

        # Add the column
        print("➕ Adding 'model_id' column to conversations table...")
        cursor.execute("ALTER TABLE conversations ADD COLUMN model_id TEXT")

        conn.commit()
        conn.close()

        print("✅ Migration completed successfully!")
        print("ℹ️  Existing conversations will use the active model by default")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    migrate()
