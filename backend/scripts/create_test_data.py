"""
Create test LLM usage data script
"""

import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import get_logger

logger = get_logger(__name__)


def create_test_llm_usage():
    """Create test LLM usage data"""

    # Find database file
    db_paths = [
        Path(__file__).parent.parent.parent / "ido.db",
        Path(__file__).parent.parent.parent / "data" / "ido.db",
        Path.home() / ".ido" / "ido.db",
    ]

    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        print("No database file found, will create in current directory")
        db_path = Path("ido.db")

    print(f"Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create llm_token_usage table (if not exists)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cost REAL DEFAULT 0.0,
            request_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Clear existing test data
    cursor.execute("DELETE FROM llm_token_usage")

    # Generate test data
    models = ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet", "gpt-4o"]
    request_types = ["summarization", "agent", "chat", "analysis"]

    test_data = []
    base_date = datetime.now() - timedelta(days=30)

    for day in range(30):
        current_date = base_date + timedelta(days=day)

        # 3-8 calls per day
        daily_calls = 3 + (day % 6)

        for call in range(daily_calls):
            model = models[call % len(models)]
            request_type = request_types[call % len(request_types)]

            prompt_tokens = 500 + (call * 150) + (day * 10)
            completion_tokens = 200 + (call * 50) + (day * 5)
            total_tokens = prompt_tokens + completion_tokens

            # Estimate cost (gpt-4: $0.03/1K prompt + $0.06/1K completion)
            if model.startswith("gpt-4"):
                cost = (prompt_tokens * 0.03 / 1000) + (completion_tokens * 0.06 / 1000)
            elif model == "gpt-3.5-turbo":
                cost = (prompt_tokens * 0.0015 / 1000) + (
                    completion_tokens * 0.002 / 1000
                )
            elif model.startswith("claude"):
                cost = (prompt_tokens * 0.015 / 1000) + (
                    completion_tokens * 0.075 / 1000
                )
            else:
                cost = total_tokens * 0.00001

            timestamp = current_date.replace(
                hour=9 + (call % 6),  # Ensure hour is in reasonable range
                minute=(call * 10) % 60, # Ensure minute is in 0-59 range
                second=0,
            ).isoformat()

            test_data.append(
                (
                    timestamp,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    round(cost, 6),
                    request_type,
                )
            )

    # Insert test data
cursor.executemany(
"""

        INSERT INTO llm_token_usage
        (timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost, request_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        test_data,
            )


    # Get statistics
    cursor.execute("""
        SELECT
            COUNT(*) as total_calls,
            SUM(total_tokens) as total_tokens,
            SUM(cost) as total_cost,
            GROUP_CONCAT(DISTINCT model) as models_used
        FROM llm_token_usage
    """)

    stats = cursor.fetchone()

    print(f"✓ Created {stats[0]} LLM usage records")
    print(f"✓ Total tokens: {stats[1],}")
    print(f"✓ Total cost: ${stats[2]:.6f}")
    print(f"✓ Models used: {stats[3]}")

    conn.commit()
    conn.close()

    print("Test data creation completed!")


if __name__ == "__main__":
    create_test_llm_usage()
