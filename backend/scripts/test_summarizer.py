#!/usr/bin/env python3
"""
测试总结器功能
专门测试 LLM 总结和事件处理
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import RawRecord, RecordType
from processing.summarizer import EventSummarizer
from processing.filter_rules import EventFilter
from core.logger import get_logger

logger = get_logger(__name__)


async def test_summarizer():
    """测试总结器功能"""
    print("🧠 启动 iDO 总结器测试...")
    print("=" * 60)
    
    try:
        # 创建总结器
        summarizer = EventSummarizer()
        print("✅ 总结器初始化成功")
        
        # 创建测试数据
        print("\n📋 创建测试数据...")
        test_records = create_test_records()
        print(f"✅ 创建了 {len(test_records)} 条测试记录")
        
        # 显示测试数据
        print("\n📝 测试数据详情:")
        for i, record in enumerate(test_records, 1):
            timestamp = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
            if record.type == RecordType.KEYBOARD_RECORD:
                key = record.data.get("key", "unknown")
                action = record.data.get("action", "unknown")
                modifiers = record.data.get("modifiers", [])
                mod_str = f" +{'+'.join(modifiers)}" if modifiers else ""
                print(f"   {i:2d}. ⌨️  [{timestamp}] 键盘: {key}{mod_str} ({action})")
            elif record.type == RecordType.MOUSE_RECORD:
                action = record.data.get("action", "unknown")
                button = record.data.get("button", "unknown")
                if "position" in record.data:
                    pos = record.data["position"]
                    print(f"   {i:2d}. 🖱️  [{timestamp}] 鼠标: {action} ({button}) at {pos}")
                else:
                    print(f"   {i:2d}. 🖱️  [{timestamp}] 鼠标: {action} ({button})")
            elif record.type == RecordType.SCREENSHOT_RECORD:
                width = record.data.get("width", 0)
                height = record.data.get("height", 0)
                print(f"   {i:2d}. 📸 [{timestamp}] 截图: {width}x{height}")
        
        # 测试事件筛选
        print(f"\n🔍 测试事件筛选...")
        filter_rules = EventFilter()
        filtered_records = filter_rules.filter_all_events(test_records)
        print(f"✅ 筛选后剩余 {len(filtered_records)} 条记录")
        
        if not filtered_records:
            print("❌ 筛选后无有效记录，无法测试总结功能")
            return
        
        # 测试总结功能
        print(f"\n🧠 测试 LLM 总结功能...")
        print("⏳ 正在调用 LLM API 进行总结...")
        
        summary = await summarizer.summarize_events(filtered_records)
        
        print(f"✅ 总结完成!")
        print(f"\n📄 总结结果:")
        print(f"   {summary}")
        
        # 测试活动总结
        print(f"\n🎯 测试活动总结...")
        activity_summary = await summarizer.summarize_activity(filtered_records)
        
        print(f"✅ 活动总结完成!")
        print(f"\n📄 活动总结:")
        print(f"   {activity_summary}")
        
        # 测试不同场景的总结
        print(f"\n🎭 测试不同场景的总结...")
        
        # 场景1: 纯键盘输入
        keyboard_records = [r for r in filtered_records if r.type == RecordType.KEYBOARD_RECORD]
        if keyboard_records:
            print(f"\n   📝 键盘输入场景 ({len(keyboard_records)} 条记录):")
            keyboard_summary = await summarizer.summarize_events(keyboard_records)
            print(f"      {keyboard_summary}")
        
        # 场景2: 纯鼠标操作
        mouse_records = [r for r in filtered_records if r.type == RecordType.MOUSE_RECORD]
        if mouse_records:
            print(f"\n   🖱️  鼠标操作场景 ({len(mouse_records)} 条记录):")
            mouse_summary = await summarizer.summarize_events(mouse_records)
            print(f"      {mouse_summary}")
        
        # 场景3: 混合操作
        print(f"\n   🔄 混合操作场景 ({len(filtered_records)} 条记录):")
        mixed_summary = await summarizer.summarize_events(filtered_records)
        print(f"      {mixed_summary}")
        
        print(f"\n✅ 总结器测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        logger.error(f"测试错误: {e}")
        import traceback
        traceback.print_exc()


def create_test_records():
    """创建测试记录"""
    base_time = datetime.now()
    records = []
    
    # 场景: 编写邮件
    print("   📧 创建场景: 编写邮件")
    
    # 输入收件人
    email_text = "Dear John,\n\nI hope this email finds you well. I wanted to follow up on our meeting yesterday.\n\nBest regards,\nAlice"
    
    for i, char in enumerate(email_text):
        records.append(RawRecord(
            timestamp=base_time + timedelta(seconds=i * 0.1),
            type=RecordType.KEYBOARD_RECORD,
            data={
                "key": char,
                "action": "press",
                "modifiers": [],
                "key_type": "char"
            }
        ))
    
    # 选择全部文本 (Ctrl+A)
    records.append(RawRecord(
        timestamp=base_time + timedelta(seconds=len(email_text) * 0.1 + 1),
        type=RecordType.KEYBOARD_RECORD,
        data={
            "key": "a",
            "action": "press",
            "modifiers": ["ctrl"],
            "key_type": "char"
        }
    ))
    
    # 复制 (Ctrl+C)
    records.append(RawRecord(
        timestamp=base_time + timedelta(seconds=len(email_text) * 0.1 + 1.2),
        type=RecordType.KEYBOARD_RECORD,
        data={
            "key": "c",
            "action": "press",
            "modifiers": ["ctrl"],
            "key_type": "char"
        }
    ))
    
    # 鼠标点击发送按钮
    records.append(RawRecord(
        timestamp=base_time + timedelta(seconds=len(email_text) * 0.1 + 2),
        type=RecordType.MOUSE_RECORD,
        data={
            "action": "press",
            "button": "left",
            "position": [800, 600]
        }
    ))
    
    records.append(RawRecord(
        timestamp=base_time + timedelta(seconds=len(email_text) * 0.1 + 2.1),
        type=RecordType.MOUSE_RECORD,
        data={
            "action": "release",
            "button": "left",
            "position": [800, 600]
        }
    ))
    
    # 添加截图
    records.append(RawRecord(
        timestamp=base_time + timedelta(seconds=len(email_text) * 0.1 + 3),
        type=RecordType.SCREENSHOT_RECORD,
        data={
            "action": "capture",
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "size_bytes": 350000,
            "file_path": f"/tmp/email_screenshot.jpg"
        }
    ))
    
    # 滚动查看邮件列表
    for i in range(3):
        records.append(RawRecord(
            timestamp=base_time + timedelta(seconds=len(email_text) * 0.1 + 4 + i * 0.5),
            type=RecordType.MOUSE_RECORD,
            data={
                "action": "scroll",
                "button": "middle",
                "position": [400, 300],
                "delta": [0, -100]
            }
        ))
    
    return records


if __name__ == "__main__":
    print("🎯 iDO 总结器测试")
    print("这个测试将展示 LLM 总结功能")
    print("包括事件筛选、文本格式化、LLM API 调用等")
    print()
    
    try:
        asyncio.run(test_summarizer())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n💥 测试失败: {e}")
        sys.exit(1)
