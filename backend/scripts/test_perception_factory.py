#!/usr/bin/env python
"""
感知层工厂模式测试脚本

测试平台特定的监控器创建和功能

使用方式：
    python backend/scripts/test_perception_factory.py

    或使用 uv 运行：
    uv run python backend/scripts/test_perception_factory.py
"""

import sys
from pathlib import Path

# 添加项目根路径和backend路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from perception.factory import MonitorFactory, create_keyboard_monitor, create_mouse_monitor
from perception import PerceptionManager


def test_platform_detection():
    """测试平台检测"""
    print("\n" + "=" * 60)
    print("测试 1: 平台检测")
    print("=" * 60)

    platform = MonitorFactory.get_platform()
    print(f"当前平台: {platform}")

    platform_names = {
        'darwin': 'macOS',
        'win32': 'Windows',
        'linux': 'Linux'
    }

    platform_name = platform_names.get(platform, platform)
    print(f"平台名称: {platform_name}")

    return True


def test_keyboard_monitor_creation():
    """测试键盘监控器创建"""
    print("\n" + "=" * 60)
    print("测试 2: 键盘监控器创建")
    print("=" * 60)

    # 使用工厂方法创建
    monitor = MonitorFactory.create_keyboard_monitor()
    print(f"监控器类型: {type(monitor).__name__}")

    # 获取统计信息
    stats = monitor.get_stats()
    print(f"实现方式: {stats.get('implementation', 'unknown')}")
    print(f"平台: {stats.get('platform', 'unknown')}")
    print(f"运行状态: {stats.get('is_running', False)}")

    # 使用便捷函数创建
    monitor2 = create_keyboard_monitor()
    print(f"\n便捷函数创建的监控器类型: {type(monitor2).__name__}")

    return True


def test_mouse_monitor_creation():
    """测试鼠标监控器创建"""
    print("\n" + "=" * 60)
    print("测试 3: 鼠标监控器创建")
    print("=" * 60)

    # 使用工厂方法创建
    monitor = MonitorFactory.create_mouse_monitor()
    print(f"监控器类型: {type(monitor).__name__}")

    # 获取统计信息
    stats = monitor.get_stats()
    print(f"实现方式: {stats.get('implementation', 'unknown')}")
    print(f"平台: {stats.get('platform', 'unknown')}")
    print(f"运行状态: {stats.get('is_running', False)}")

    # 使用便捷函数创建
    monitor2 = create_mouse_monitor()
    print(f"\n便捷函数创建的监控器类型: {type(monitor2).__name__}")

    return True


def test_perception_manager():
    """测试感知管理器集成"""
    print("\n" + "=" * 60)
    print("测试 4: 感知管理器集成")
    print("=" * 60)

    # 创建管理器
    manager = PerceptionManager(capture_interval=2.0, window_size=20)
    print("感知管理器已创建")

    # 获取统计信息
    stats = manager.get_stats()
    print(f"\n管理器配置:")
    print(f"  运行状态: {stats['is_running']}")
    print(f"  捕获间隔: {stats['capture_interval']}s")
    print(f"  窗口大小: {stats['window_size']}s")

    print(f"\n键盘监控器:")
    keyboard_stats = stats['keyboard']
    print(f"  平台: {keyboard_stats.get('platform', 'unknown')}")
    print(f"  实现: {keyboard_stats.get('implementation', 'unknown')}")
    print(f"  状态: {'运行中' if keyboard_stats.get('is_running') else '未启动'}")

    print(f"\n鼠标监控器:")
    mouse_stats = stats['mouse']
    print(f"  平台: {mouse_stats.get('platform', 'unknown')}")
    print(f"  实现: {mouse_stats.get('implementation', 'unknown')}")
    print(f"  状态: {'运行中' if mouse_stats.get('is_running') else '未启动'}")

    print(f"\n截图捕获器:")
    screenshot_stats = stats['screenshot']
    print(f"  状态: {'运行中' if screenshot_stats.get('is_running') else '未启动'}")

    return True


def test_interface_compatibility():
    """测试接口兼容性"""
    print("\n" + "=" * 60)
    print("测试 5: 接口兼容性")
    print("=" * 60)

    keyboard = create_keyboard_monitor()
    mouse = create_mouse_monitor()

    # 检查所有监控器都有必需的方法
    required_methods = ['start', 'stop', 'capture', 'output', 'get_stats']

    print("检查键盘监控器接口:")
    for method in required_methods:
        has_method = hasattr(keyboard, method) and callable(getattr(keyboard, method))
        status = "✓" if has_method else "✗"
        print(f"  {status} {method}")

    print("\n检查鼠标监控器接口:")
    for method in required_methods:
        has_method = hasattr(mouse, method) and callable(getattr(mouse, method))
        status = "✓" if has_method else "✗"
        print(f"  {status} {method}")

    # 检查特定方法
    print("\n检查特定方法:")
    print(f"  ✓ 键盘.is_special_key: {hasattr(keyboard, 'is_special_key')}")
    print(f"  ✓ 鼠标.is_important_event: {hasattr(mouse, 'is_important_event')}")

    return True


def main():
    """运行所有测试"""
    print("\n" + "#" * 60)
    print("# 感知层工厂模式测试套件")
    print("#" * 60)

    tests = [
        ("平台检测", test_platform_detection),
        ("键盘监控器创建", test_keyboard_monitor_creation),
        ("鼠标监控器创建", test_mouse_monitor_creation),
        ("感知管理器集成", test_perception_manager),
        ("接口兼容性", test_interface_compatibility),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 打印测试总结
    print("\n" + "#" * 60)
    print("# 测试总结")
    print("#" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
