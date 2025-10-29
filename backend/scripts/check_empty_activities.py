#!/usr/bin/env python3
"""
检查数据库中是否存在 source_events 为空的活动
"""

import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_db

def check_empty_activities():
    """检查是否有空的 source_events"""
    print("🔍 检查数据库中的活动...")
    print("=" * 60)

    db = get_db()

    # 查询所有活动
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
            print(f"❌ NULL source_events: {activity['id'][:8]}... - {activity['description'][:50]}")
        elif source_events == "":
            empty_count += 1
            print(f"❌ EMPTY source_events: {activity['id'][:8]}... - {activity['description'][:50]}")
        else:
            try:
                events = json.loads(source_events) if isinstance(source_events, str) else source_events
                if len(events) == 0:
                    empty_count += 1
                    print(f"❌ ZERO events: {activity['id'][:8]}... - {activity['description'][:50]}")
                else:
                    valid_count += 1
            except Exception as e:
                print(f"⚠️  JSON parse error: {activity['id'][:8]}... - {e}")

    print("\n" + "=" * 60)
    print(f"📊 统计结果:")
    print(f"  ✓ 有效活动: {valid_count}")
    print(f"  ✗ 空数组: {empty_count}")
    print(f"  ✗ NULL: {null_count}")
    print(f"  总计: {len(activities)}")

    if empty_count > 0 or null_count > 0:
        print(f"\n⚠️  发现 {empty_count + null_count} 个活动没有事件数据！")
        print("这就是前端显示'暂无事件摘要'的原因。")
        return False
    else:
        print("\n✅ 所有活动都有事件数据")
        return True

if __name__ == "__main__":
    check_empty_activities()
