#!/usr/bin/env python3
"""
简单的Dashboard功能测试脚本

测试DashboardManager的各项功能：
- LLM统计查询
- 使用量摘要
- 数据记录
"""

import sys
import sqlite3
from pathlib import Path

# 添加backend目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from core.dashboard.manager import get_dashboard_manager, UsageStatsSummary
from core.logger import get_logger

logger = get_logger(__name__)

def test_dashboard_manager():
    """测试DashboardManager功能"""
    print("🧪 开始测试Dashboard功能...")

    # 获取DashboardManager实例
    manager = get_dashboard_manager()

    # 测试1: 获取LLM统计
    print("\n1️⃣ 测试LLM统计查询:")
    try:
        llm_stats = manager.get_llm_statistics(days=30)
        print(f"   ✅ 总Token数: {llm_stats.total_tokens:,}")
        print(f"   ✅ 总调用次数: {llm_stats.total_calls}")
        print(f"   ✅ 总费用: ${llm_stats.total_cost:.6f}")
        print(f"   ✅ 使用模型: {', '.join(llm_stats.models_used)}")
        print(f"   ✅ 每日数据条数: {len(llm_stats.daily_usage)}")
    except Exception as e:
        print(f"   ❌ LLM统计查询失败: {e}")

    # 测试2: 获取使用量摘要
    print("\n2️⃣ 测试使用量摘要:")
    try:
        summary = manager.get_usage_summary()
        print(f"   ✅ 活动总数: {summary.activities_total}")
        print(f"   ✅ 任务总数: {summary.tasks_total}")
        print(f"   ✅ 已完成任务: {summary.tasks_completed}")
        print(f"   ✅ 待办任务: {summary.tasks_pending}")
        print(f"   ✅ 最近7天Token: {summary.llm_tokens_last_7_days}")
        print(f"   ✅ 最近7天调用: {summary.llm_calls_last_7_days}")
        print(f"   ✅ 最近7天费用: ${summary.llm_cost_last_7_days:.6f}")
    except Exception as e:
        print(f"   ❌ 使用量摘要获取失败: {e}")

    # 测试3: 获取每日LLM使用
    print("\n3️⃣ 测试每日LLM使用情况:")
    try:
        daily_usage = manager.get_daily_llm_usage(days=7)
        print(f"   ✅ 获取到 {len(daily_usage)} 条每日记录")
        if daily_usage:
            latest = daily_usage[0]
            print(f"   📊 最新记录: {latest['date']} - {latest['tokens']} tokens")
    except Exception as e:
        print(f"   ❌ 每日使用情况获取失败: {e}")

    # 测试4: 获取模型使用分布
    print("\n4️⃣ 测试模型使用分布:")
    try:
        model_dist = manager.get_model_usage_distribution(days=30)
        print(f"   ✅ 获取到 {len(model_dist)} 个模型的使用数据")
        for model in model_dist:
            print(f"   📊 {model['model']}: {model['calls']} 次调用, {model['total_tokens']} tokens")
    except Exception as e:
        print(f"   ❌ 模型分布获取失败: {e}")

    # 测试5: 记录新的LLM使用
    print("\n5️⃣ 测试记录LLM使用:")
    try:
        success = manager.record_llm_usage(
            model="test-model",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost=0.001,
            request_type="test"
        )
        print(f"   {'✅' if success else '❌'} 记录测试LLM使用: {success}")
    except Exception as e:
        print(f"   ❌ 记录LLM使用失败: {e}")

    print("\n🎉 Dashboard功能测试完成!")


if __name__ == "__main__":
    test_dashboard_manager()
