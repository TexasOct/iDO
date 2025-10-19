#!/usr/bin/env python3
"""
Perception 模块演示脚本
展示键盘、鼠标、屏幕截图捕获功能
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.manager import PerceptionManager
from core.logger import get_logger

logger = get_logger(__name__)


async def demo_perception():
    """演示感知模块功能"""
    print("🚀 启动 Rewind Perception 演示...")
    print("=" * 50)
    
    # 创建感知管理器
    manager = PerceptionManager(
        capture_interval=0.5,  # 每0.5秒截图一次
        window_size=10,        # 10秒滑动窗口
        on_data_captured=on_data_captured
    )
    
    try:
        # 启动管理器
        print("📡 启动感知管理器...")
        await manager.start()
        
        print("✅ 感知管理器已启动！")
        print("\n📋 现在请进行一些操作：")
        print("   - 移动鼠标")
        print("   - 点击鼠标")
        print("   - 按键盘（特别是特殊键如 Enter, Space, Ctrl+C 等）")
        print("   - 滚动鼠标滚轮")
        print("\n⏱️  演示将持续 30 秒...")
        print("=" * 50)
        
        # 运行 30 秒
        for i in range(30):
            await asyncio.sleep(1)
            
            # 每5秒显示一次统计信息
            if (i + 1) % 5 == 0:
                stats = manager.get_stats()
                print(f"\n📊 统计信息 (第 {i+1} 秒):")
                print(f"   - 总记录数: {stats['storage']['total_records']}")
                print(f"   - 键盘事件: {stats['storage']['type_counts'].get('keyboard_event', 0)}")
                print(f"   - 鼠标事件: {stats['storage']['type_counts'].get('mouse_event', 0)}")
                print(f"   - 屏幕截图: {stats['storage']['type_counts'].get('screenshot', 0)}")
                print(f"   - 缓冲区大小: {stats['buffer_size']}")
        
        # 显示最终结果
        print("\n" + "=" * 50)
        print("📈 最终统计:")
        final_stats = manager.get_stats()
        print(f"   - 总记录数: {final_stats['storage']['total_records']}")
        print(f"   - 键盘事件: {final_stats['storage']['type_counts'].get('keyboard_event', 0)}")
        print(f"   - 鼠标事件: {final_stats['storage']['type_counts'].get('mouse_event', 0)}")
        print(f"   - 屏幕截图: {final_stats['storage']['type_counts'].get('screenshot', 0)}")
        
        # 显示最近的记录
        recent_records = manager.get_recent_records(10)
        if recent_records:
            print(f"\n📝 最近 {len(recent_records)} 条记录:")
            for i, record in enumerate(recent_records[-5:], 1):  # 只显示最后5条
                timestamp = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
                event_type = record.type.value
                if event_type == "keyboard_event":
                    key = record.data.get("key", "unknown")
                    action = record.data.get("action", "unknown")
                    print(f"   {i}. [{timestamp}] 键盘: {key} ({action})")
                elif event_type == "mouse_event":
                    action = record.data.get("action", "unknown")
                    button = record.data.get("button", "unknown")
                    print(f"   {i}. [{timestamp}] 鼠标: {action} ({button})")
                elif event_type == "screenshot":
                    width = record.data.get("width", 0)
                    height = record.data.get("height", 0)
                    print(f"   {i}. [{timestamp}] 截图: {width}x{height}")
        
    except KeyboardInterrupt:
        print("\n⏹️  用户中断演示")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        logger.error(f"演示错误: {e}")
    finally:
        # 停止管理器
        print("\n🛑 停止感知管理器...")
        await manager.stop()
        print("✅ 演示结束！")


def on_data_captured(record):
    """数据捕获回调函数"""
    timestamp = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
    event_type = record.type.value
    
    if event_type == "keyboard_event":
        key = record.data.get("key", "unknown")
        action = record.data.get("action", "unknown")
        modifiers = record.data.get("modifiers", [])
        mod_str = f" +{'+'.join(modifiers)}" if modifiers else ""
        print(f"⌨️  [{timestamp}] 键盘: {key}{mod_str} ({action})")
    
    elif event_type == "mouse_event":
        action = record.data.get("action", "unknown")
        button = record.data.get("button", "unknown")
        if "position" in record.data:
            pos = record.data["position"]
            print(f"🖱️  [{timestamp}] 鼠标: {action} ({button}) at {pos}")
        else:
            print(f"🖱️  [{timestamp}] 鼠标: {action} ({button})")
    
    elif event_type == "screenshot":
        width = record.data.get("width", 0)
        height = record.data.get("height", 0)
        size_bytes = record.data.get("size_bytes", 0)
        size_kb = size_bytes / 1024
        print(f"📸 [{timestamp}] 截图: {width}x{height} ({size_kb:.1f}KB)")


if __name__ == "__main__":
    print("🎯 Rewind Perception 模块演示")
    print("这个演示将展示键盘、鼠标和屏幕截图的实时捕获功能")
    print("注意：在某些系统上可能需要权限才能捕获输入事件")
    print()
    
    try:
        asyncio.run(demo_perception())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n💥 演示失败: {e}")
        sys.exit(1)
