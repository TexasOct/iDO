#!/usr/bin/env python3
"""
真实监听测试脚本
实际监听用户的键盘、鼠标和屏幕截图操作，然后生成事件和总结
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.manager import PerceptionManager
from core.logger import get_logger

logger = get_logger(__name__)


async def test_real_capture():
    """真实监听测试 - 监听10秒并输出时间轴"""
    print("🎯 iDO 真实监听测试")
    print("=" * 60)
    print("这个测试将实际监听你的键盘、鼠标和屏幕操作")
    print("请在这 10 秒内进行一些操作，比如：")
    print("  - 打字、使用快捷键")
    print("  - 移动鼠标、点击、滚动")
    print("  - 切换窗口、浏览网页")
    print("=" * 60)
    
    # 创建感知管理器
    perception_manager = PerceptionManager(
        capture_interval=0.1,  # 每0.1秒截图一次，提高精度
        window_size=10,        # 10秒滑动窗口
        on_data_captured=None  # 不实时输出，最后统一按时间轴输出
    )
    
    try:
        # 启动感知管理器
        print("📡 启动感知管理器...")
        await perception_manager.start()
        print("✅ 感知管理器已启动！")
        
        print(f"\n⏱️  开始监听，持续 10 秒...")
        print("=" * 60)
        
        # 监听 10 秒
        for i in range(10):
            await asyncio.sleep(1)
            print(f"⏰ 监听中... {i+1}/10 秒")
        
        print(f"\n⏹️  监听结束！")
        print("=" * 60)
        
        # 获取所有捕获的记录
        all_records = perception_manager.get_recent_records(1000)  # 获取最近1000条记录
        print(f"📋 总共捕获了 {len(all_records)} 条记录")
        
        if not all_records:
            print("❌ 没有捕获到任何记录，请确保有权限访问输入设备")
            return
        
        # 按时间戳排序所有记录
        all_records.sort(key=lambda x: x.timestamp)
        
        # 按时间轴输出所有raw_records
        print(f"\n📝 时间轴输出所有raw_records:")
        print("=" * 60)
        
        for i, record in enumerate(all_records, 1):
            timestamp = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
            record_type = record.type.value
            
            # if record_type == "keyboard_record":
            #     key = record.data.get("key", "unknown")
            #     action = record.data.get("action", "unknown")
            #     modifiers = record.data.get("modifiers", [])
            #     mod_str = f" +{'+'.join(modifiers)}" if modifiers else ""
            #     print(f"{i:3d}. ⌨️  [{timestamp}] 键盘: {key}{mod_str} ({action})")
                
            # elif record_type == "mouse_record":
            #     action = record.data.get("action", "unknown")
            #     button = record.data.get("button", "unknown")
            #     if "position" in record.data:
            #         pos = record.data["position"]
            #         print(f"{i:3d}. 🖱️  [{timestamp}] 鼠标: {action} ({button}) at {pos}")
            #     else:
            #         print(f"{i:3d}. 🖱️  [{timestamp}] 鼠标: {action} ({button})")
                    
            # elif record_type == "screenshot_record":
            #     width = record.data.get("width", 0)
            #     height = record.data.get("height", 0)
            #     size_bytes = record.data.get("size_bytes", 0)
            #     size_kb = size_bytes / 1024 if size_bytes > 0 else 0
            #     print(f"{i:3d}. 📸 [{timestamp}] 截图: {width}x{height} ({size_kb:.1f}KB)")

            print(record)
        
        # 显示统计信息
        print(f"\n📊 记录统计:")
        print("=" * 60)
        keyboard_count = sum(1 for r in all_records if r.type.value == "keyboard_record")
        mouse_count = sum(1 for r in all_records if r.type.value == "mouse_record")
        screenshot_count = sum(1 for r in all_records if r.type.value == "screenshot_record")
        
        print(f"   - 总记录数: {len(all_records)}")
        print(f"   - 键盘事件: {keyboard_count}")
        print(f"   - 鼠标事件: {mouse_count}")
        print(f"   - 屏幕截图: {screenshot_count}")
        
        if all_records:
            start_time = all_records[0].timestamp
            end_time = all_records[-1].timestamp
            duration = (end_time - start_time).total_seconds()
            print(f"   - 时间范围: {start_time.strftime('%H:%M:%S.%f')[:-3]} - {end_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"   - 实际时长: {duration:.2f} 秒")
        
        print(f"\n✅ 真实监听测试完成！")
        
    except KeyboardInterrupt:
        print("\n⏹️  用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        logger.error(f"测试错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 停止管理器
        print("\n🛑 停止感知管理器...")
        await perception_manager.stop()
        print("✅ 测试结束！")


if __name__ == "__main__":
    print("🎯 iDO 真实监听测试")
    print("这个测试将实际监听你的操作并生成事件总结")
    print("注意：在某些系统上可能需要权限才能捕获输入事件")
    print()
    
    try:
        asyncio.run(test_real_capture())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n💥 测试失败: {e}")
        sys.exit(1)
