"""
创建测试LLM使用数据脚本
Create test LLM usage data script
"""

import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# 添加backend目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import get_logger

logger = get_logger(__name__)

def create_test_llm_usage():
    """创建测试LLM使用数据"""

    # 查找数据库文件
    db_paths = [
        Path(__file__).parent.parent.parent / "rewind.db",
        Path(__file__).parent.parent.parent / "data" / "rewind.db",
        Path.home() / ".rewind" / "rewind.db"
    ]

    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        print("未找到数据库文件，将在当前目录创建")
        db_path = Path("rewind.db")

    print(f"使用数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建llm_token_usage表（如果不存在）
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

    # 清空现有测试数据
    cursor.execute("DELETE FROM llm_token_usage")

    # 生成测试数据
    models = ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet", "gpt-4o"]
    request_types = ["summarization", "agent", "chat", "analysis"]

    test_data = []
    base_date = datetime.now() - timedelta(days=30)

    for day in range(30):
        current_date = base_date + timedelta(days=day)

        # 每天3-8次调用
        daily_calls = 3 + (day % 6)

        for call in range(daily_calls):
            model = models[call % len(models)]
            request_type = request_types[call % len(request_types)]

            prompt_tokens = 500 + (call * 150) + (day * 10)
            completion_tokens = 200 + (call * 50) + (day * 5)
            total_tokens = prompt_tokens + completion_tokens

            # 估算成本 (gpt-4: $0.03/1K prompt + $0.06/1K completion)
            if model.startswith("gpt-4"):
                cost = (prompt_tokens * 0.03 / 1000) + (completion_tokens * 0.06 / 1000)
            elif model == "gpt-3.5-turbo":
                cost = (prompt_tokens * 0.0015 / 1000) + (completion_tokens * 0.002 / 1000)
            elif model.startswith("claude"):
                cost = (prompt_tokens * 0.015 / 1000) + (completion_tokens * 0.075 / 1000)
            else:
                cost = total_tokens * 0.00001

            timestamp = current_date.replace(
                hour=9 + (call % 6),  # 确保 hour 在合理范围内
                minute=(call * 10) % 60,  # 确保 minute 在 0-59 范围内
                second=0
            ).isoformat()

            test_data.append((
                timestamp,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                round(cost, 6),
                request_type
            ))

    # 插入测试数据
    cursor.executemany("""
        INSERT INTO llm_token_usage
        (timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost, request_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, test_data)

    # 获取统计信息
    cursor.execute("""
        SELECT
            COUNT(*) as total_calls,
            SUM(total_tokens) as total_tokens,
            SUM(cost) as total_cost,
            GROUP_CONCAT(DISTINCT model) as models_used
        FROM llm_token_usage
    """)

    stats = cursor.fetchone()

    print(f"✓ 创建了 {stats[0]} 条LLM使用记录")
    print(f"✓ 总token数: {stats[1]:,}")
    print(f"✓ 总费用: ${stats[2]:.6f}")
    print(f"✓ 使用的模型: {stats[3]}")

    conn.commit()
    conn.close()

    print("测试数据创建完成！")

if __name__ == "__main__":
    create_test_llm_usage()
