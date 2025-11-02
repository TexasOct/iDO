#!/usr/bin/env python3
"""
真实监听测试脚本 - 事件聚合版本
实际监听用户的键盘、鼠标和屏幕截图操作，然后聚合成events并输出
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.manager import PerceptionManager
from processing.pipeline import ProcessingPipeline
from core.logger import get_logger

logger = get_logger(__name__)


async def test_events_capture():
    """真实监听测试 - 监听50秒并聚合为events"""
    print("🎯 Rewind 事件聚合测试")
    print("=" * 60)
    print("这个测试将实际监听你的键盘、鼠标和屏幕操作")
    print("然后聚合成events并输出")
    print("📸 截图将自动保存到 backend/tmp/screenshots/ 文件夹")
    print("请在这 50 秒内进行一些操作，比如：")
    print("  - 打字、使用快捷键")
    print("  - 移动鼠标、点击、滚动")
    print("  - 切换窗口、浏览网页")
    print("=" * 60)
    
    # 创建感知管理器
    perception_manager = PerceptionManager(
        capture_interval=0.1,  # 每0.1秒截图一次，提高精度
        window_size=50,        # 50秒滑动窗口，确保覆盖整个监听时间
        on_data_captured=None  # 不实时输出，最后统一处理
    )
    
    # 创建处理管道
    processing_pipeline = ProcessingPipeline()
    
    try:
        # 启动感知管理器
        print("📡 启动感知管理器...")
        await perception_manager.start()
        print("✅ 感知管理器已启动！")
        
        # 启动处理管道
        print("🔄 启动处理管道...")
        await processing_pipeline.start()
        print("✅ 处理管道已启动！")
        
        print(f"\n⏱️  开始监听，持续 50 秒...")
        print("=" * 60)
        
        # 监听 10 秒
        for i in range(50):
            await asyncio.sleep(1)
            print(f"⏰ 监听中... {i+1}/50 秒")
        
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
        
        # 显示原始记录统计
        print(f"\n📊 原始记录统计:")
        print("=" * 60)
        keyboard_count = sum(1 for r in all_records if r.type.value == "keyboard_record")
        mouse_count = sum(1 for r in all_records if r.type.value == "mouse_record")
        screenshot_count = sum(1 for r in all_records if r.type.value == "screenshot_record")
        
        print(f"   - 总记录数: {len(all_records)}")
        print(f"   - 键盘记录: {keyboard_count}")
        print(f"   - 鼠标记录: {mouse_count}")
        print(f"   - 屏幕截图记录: {screenshot_count}")
        
        if all_records:
            start_time = all_records[0].timestamp
            end_time = all_records[-1].timestamp
            duration = (end_time - start_time).total_seconds()
            print(f"   - 时间范围: {start_time.strftime('%H:%M:%S.%f')[:-3]} - {end_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"   - 实际时长: {duration:.2f} 秒")
        
        # 处理原始记录，聚合成events
        print(f"\n🔄 开始聚合events...")
        print("=" * 60)
        
        # 一次性处理所有记录，避免分批导致的状态混乱
        all_events = []
        all_activities = []
        total_activities = 0
        
        if all_records:
            # 按时间戳排序
            all_records.sort(key=lambda x: x.timestamp)
            
            print(f"\n📦 处理所有数据 ({len(all_records)} 条记录)...")
            start_time = all_records[0].timestamp
            end_time = all_records[-1].timestamp
            print(f"   时间范围: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")
            
            # 一次性处理所有记录
            result = await processing_pipeline.process_raw_records(all_records)
            
            # 显示处理结果
            print(f"   ✅ 创建了 {len(result['events'])} 个事件")
            print(f"   ✅ 创建了 {len(result['activities'])} 个活动")
            print(f"   {'🔄 合并到现有活动' if result['merged'] else '🆕 创建新活动'}")
            
            all_events.extend(result['events'])
            total_activities += len(result['activities'])
            all_activities.extend(result['activities'])
        
        # 强制完成当前活动
        await processing_pipeline.force_finalize_activity()
        
        print(f"\n📝 聚合的Events详情:")
        print("=" * 60)
        
        if not all_events:
            print("❌ 没有生成任何事件")
            return
        
        # 按时间排序events
        all_events.sort(key=lambda x: x.start_time)
        
        for i, event in enumerate(all_events, 1):
            start_time_str = event.start_time.strftime("%H:%M:%S.%f")[:-3]
            end_time_str = event.end_time.strftime("%H:%M:%S.%f")[:-3]
            duration = (event.end_time - event.start_time).total_seconds()
            
            print(f"{i:2d}. 🎯 Event [{event.id[:8]}...]")
            print(f"     ⏰ 时间: {start_time_str} - {end_time_str} ({duration:.2f}s)")
            print(f"     📝 类型: {event.type.value}")
            print(f"     📄 摘要: {event.summary}")
            print(f"     📊 源数据: {len(event.source_data)} 条记录")
            
            # 显示该事件包含的截图
            event_screenshots = [r for r in event.source_data if r.type.value == "screenshot_record" and hasattr(r, 'screenshot_path') and r.screenshot_path]
            if event_screenshots:
                print(f"     📸 截图文件 ({len(event_screenshots)} 张):")
                for k, screenshot_record in enumerate(event_screenshots, 1):
                    screenshot_time = screenshot_record.timestamp.strftime("%H:%M:%S.%f")[:-3]
                    width = screenshot_record.data.get("width", 0)
                    height = screenshot_record.data.get("height", 0)
                    print(f"        {k}. [{screenshot_time}] {width}x{height} -> {screenshot_record.screenshot_path}")
            else:
                print(f"     📸 截图文件: 无")
            
            # 显示源数据详情
            print(f"     📋 源数据详情:")
            for j, record in enumerate(event.source_data[:5], 1):  # 只显示前5条
                record_time = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
                record_type = record.type.value
                
                if record_type == "keyboard_record":
                    key = record.data.get("key", "unknown")
                    action = record.data.get("action", "unknown")
                    modifiers = record.data.get("modifiers", [])
                    mod_str = f" +{'+'.join(modifiers)}" if modifiers else ""
                    print(f"        {j}. ⌨️  [{record_time}] {key}{mod_str} ({action})")
                elif record_type == "mouse_record":
                    action = record.data.get("action", "unknown")
                    button = record.data.get("button", "unknown")
                    if "position" in record.data:
                        pos = record.data["position"]
                        print(f"        {j}. 🖱️  [{record_time}] {action} ({button}) at {pos}")
                    else:
                        print(f"        {j}. 🖱️  [{record_time}] {action} ({button})")
                elif record_type == "screenshot_record":
                    width = record.data.get("width", 0)
                    height = record.data.get("height", 0)
                    screenshot_path = getattr(record, 'screenshot_path', None)
                    if screenshot_path:
                        print(f"        {j}. 📸 [{record_time}] {width}x{height} -> {screenshot_path}")
                    else:
                        print(f"        {j}. 📸 [{record_time}] {width}x{height}")
            
            if len(event.source_data) > 5:
                print(f"        ... 还有 {len(event.source_data) - 5} 条记录")
            
            print()  # 空行分隔
        
        print("--------------------------------")
        print("聚合的Activities详情:")
        print("=" * 60)
        
        if all_activities:
            for i, activity in enumerate(all_activities, 1):
                activity_id = activity.get('id', 'unknown')
                start_time = activity.get('start_time')
                end_time = activity.get('end_time')
                description = activity.get('description', '未知活动')
                event_count = activity.get('event_count', 0)
                
                # 格式化时间显示
                if start_time and end_time:
                    start_str = start_time.strftime('%H:%M:%S.%f')[:-3] if hasattr(start_time, 'strftime') else str(start_time)
                    end_str = end_time.strftime('%H:%M:%S.%f')[:-3] if hasattr(end_time, 'strftime') else str(end_time)
                    duration = (end_time - start_time).total_seconds() if hasattr(end_time, '__sub__') and hasattr(start_time, '__sub__') else 0
                    duration_str = f"({duration:.2f}s)"
                else:
                    start_str = "未知"
                    end_str = "未知"
                    duration_str = ""
                
                print(f"{i:2d}. 🎯 Activity [{activity_id[:8]}...]")
                print(f"     ⏰ 时间: {start_str} - {end_str} {duration_str}")
                print(f"     📝 描述: {description}")
                print(f"     📊 事件数: {event_count}")
                
                # 显示源事件信息
                source_events = activity.get('source_events', [])
                if source_events:
                    print(f"     📋 源事件: {len(source_events)} 个")
                    # 显示前3个源事件的简要信息
                    for j, event in enumerate(source_events[:3], 1):
                        if hasattr(event, 'summary'):
                            event_summary = event.summary
                        else:
                            event_summary = event.get('summary', '无摘要') if isinstance(event, dict) else '无摘要'
                        print(f"        {j}. {event_summary[:50]}{'...' if len(str(event_summary)) > 50 else ''}")
                    
                    if len(source_events) > 3:
                        print(f"        ... 还有 {len(source_events) - 3} 个事件")
                
                print()  # 空行分隔
        else:
            print("❌ 没有生成任何活动")

        print("--------------------------------")
        
        # 显示最终统计
        print(f"\n📈 最终统计:")
        print("=" * 60)
        print(f"   - 原始记录数: {len(all_records)}")
        print(f"   - 生成事件数: {len(all_events)}")
        print(f"   - 生成活动数: {total_activities}")
        
        # 统计截图文件
        screenshot_records = [r for r in all_records if r.type.value == "screenshot_record"]
        screenshot_files = [r for r in screenshot_records if hasattr(r, 'screenshot_path') and r.screenshot_path]
        print(f"   - 截图记录数: {len(screenshot_records)}")
        print(f"   - 截图文件数: {len(screenshot_files)}")
        
        if all_events:
            event_start = all_events[0].start_time
            event_end = all_events[-1].end_time
            total_duration = (event_end - event_start).total_seconds()
            print(f"   - 事件时间范围: {event_start.strftime('%H:%M:%S.%f')[:-3]} - {event_end.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"   - 总事件时长: {total_duration:.2f} 秒")

        

        
        print(f"\n✅ 事件聚合测试完成！")
        
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
        print("🛑 停止处理管道...")
        await processing_pipeline.stop()
        print("✅ 测试结束！")


if __name__ == "__main__":
    print("🎯 Rewind 事件聚合测试")
    print("这个测试将实际监听你的操作并聚合成events")
    print("注意：在某些系统上可能需要权限才能捕获输入事件")
    print()
    
    try:
        asyncio.run(test_events_capture())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n💥 测试失败: {e}")
        sys.exit(1)
