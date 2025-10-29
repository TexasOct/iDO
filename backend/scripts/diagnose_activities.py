#!/usr/bin/env python3
"""
详细诊断活动数据的格式和完整性
"""

import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_db

def diagnose_activities():
    """详细诊断活动数据"""
    print("🔍 详细诊断活动数据...")
    print("=" * 80)

    db = get_db()

    # 查询所有活动
    activities = db.execute_query(
        "SELECT id, description, start_time, end_time, source_events FROM activities ORDER BY start_time DESC LIMIT 20"
    )

    print(f"\n📊 总共 {len(activities)} 个活动\n")

    for i, activity in enumerate(activities, 1):
        print(f"\n{'='*80}")
        print(f"活动 #{i}")
        print(f"{'='*80}")
        print(f"ID: {activity['id']}")
        print(f"描述: {activity['description']}")
        print(f"开始时间: {activity['start_time']}")
        print(f"结束时间: {activity['end_time']}")

        source_events = activity.get("source_events")

        if source_events is None:
            print(f"❌ source_events: NULL")
            continue
        elif source_events == "":
            print(f"❌ source_events: EMPTY STRING")
            continue

        try:
            # 尝试解析 JSON
            events = json.loads(source_events) if isinstance(source_events, str) else source_events
            event_count = len(events)

            if event_count == 0:
                print(f"❌ source_events: [] (空数组)")
            else:
                print(f"✓ source_events: {event_count} 个事件")

                # 检查每个事件的格式
                for j, event in enumerate(events[:3], 1):  # 只显示前3个
                    print(f"\n  事件 #{j}:")
                    print(f"    - id: {event.get('id', 'MISSING')}")
                    print(f"    - summary: {event.get('summary', 'MISSING')[:60]}...")
                    print(f"    - start_time: {event.get('start_time', 'MISSING')}")
                    print(f"    - end_time: {event.get('end_time', 'MISSING')}")
                    print(f"    - type: {event.get('type', 'MISSING')}")

                    # 检查 source_data
                    source_data = event.get('source_data', [])
                    if isinstance(source_data, list):
                        print(f"    - source_data: {len(source_data)} 条记录")

                        # 统计 source_data 中的类型
                        types = {}
                        for record in source_data:
                            record_type = record.get('type', 'unknown')
                            types[record_type] = types.get(record_type, 0) + 1

                        print(f"      类型分布: {dict(types)}")
                    else:
                        print(f"    - source_data: ❌ 不是数组")

                if event_count > 3:
                    print(f"\n  ... 还有 {event_count - 3} 个事件")

        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            print(f"   原始数据: {source_events[:200]}...")
        except Exception as e:
            print(f"❌ 处理失败: {e}")

    print(f"\n{'='*80}")
    print("✅ 诊断完成")

if __name__ == "__main__":
    diagnose_activities()
