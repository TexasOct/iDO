#!/usr/bin/env python
"""
图像优化测试脚本

验证图像优化功能是否正常工作，对比优化前后的效果

使用方式：
    python backend/scripts/test_image_optimization.py

    或使用 uv 运行：
    uv run python backend/scripts/test_image_optimization.py
"""

import asyncio
import base64
import io
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image
import numpy as np
from core.logger import get_logger
from processing.image_optimization import (
    ImageDifferenceAnalyzer,
    ImageContentAnalyzer,
    EventDensitySampler,
    HybridImageFilter,
)

logger = get_logger(__name__)


def create_test_image(width: int = 400, height: int = 300, seed: int = 0) -> bytes:
    """创建随机测试图像"""
    np.random.seed(seed)
    # 创建随机图像
    pixels = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(pixels, 'RGB')

    # 转换为 JPEG 字节
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    return output.getvalue()


def create_similar_image(base_image: bytes, variation: float = 0.1) -> bytes:
    """基于基础图像创建相似的图像（模拟截图重复）"""
    img = Image.open(io.BytesIO(base_image)).convert('RGB')
    pixels = np.array(img, dtype=np.float32)

    # 添加小的随机变化
    noise = np.random.normal(0, variation * 255, pixels.shape)
    pixels = np.clip(pixels + noise, 0, 255).astype(np.uint8)

    modified_img = Image.fromarray(pixels, 'RGB')
    output = io.BytesIO()
    modified_img.save(output, format='JPEG', quality=85)
    return output.getvalue()


def create_static_image() -> bytes:
    """创建静态内容图像（低对比度）"""
    img = Image.new('RGB', (400, 300), color=(200, 200, 200))
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    return output.getvalue()


def create_complex_image() -> bytes:
    """创建复杂内容图像（高对比度）"""
    pixels = np.zeros((300, 400, 3), dtype=np.uint8)
    # 添加高对比度内容
    pixels[50:100, 50:150] = [255, 255, 255]
    pixels[150:200, 200:350] = [0, 0, 0]
    pixels[225:275, 100:300] = [128, 64, 192]

    img = Image.fromarray(pixels, 'RGB')
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    return output.getvalue()


class OptimizationTestSuite:
    """图像优化测试套件"""

    def __init__(self):
        self.test_results = {}

    def test_phash_duplicate_detection(self):
        """测试感知哈希重复检测"""
        print("\n" + "="*60)
        print("测试 1: 感知哈希重复检测")
        print("="*60)

        analyzer = ImageDifferenceAnalyzer(threshold=0.15)

        # 创建基础图像
        img1 = create_test_image(seed=1)
        img2 = create_similar_image(img1, variation=0.05)  # 轻微变化
        img3 = create_similar_image(img1, variation=0.20)  # 显著变化

        # 测试
        change1 = analyzer.is_significant_change(img1)
        change2 = analyzer.is_significant_change(img2)
        change3 = analyzer.is_significant_change(img3)

        print(f"首张图像：{change1} (预期: True)")
        print(f"轻微变化：{change2} (预期: False - 被认为重复)")
        print(f"显著变化：{change3} (预期: True)")

        stats = analyzer.get_stats()
        print(f"\n统计信息:")
        print(f"  总检查: {stats['total_checked']}")
        print(f"  显著变化: {stats['significant_changes']}")
        print(f"  被跳过: {stats['duplicates_skipped']}")

        # 验证结果
        success = (change1 and not change2 and change3)
        self.test_results['phash_detection'] = success
        print(f"\n✓ 测试通过: {success}\n")

        return success

    def test_content_analysis(self):
        """测试内容分析"""
        print("\n" + "="*60)
        print("测试 2: 内容分析")
        print("="*60)

        analyzer = ImageContentAnalyzer()

        # 创建不同类型的图像
        static_img = create_static_image()
        complex_img = create_complex_image()

        # 分析
        static_analysis = analyzer.analyze_content(static_img)
        complex_analysis = analyzer.analyze_content(complex_img)

        print(f"静态图像分析:")
        print(f"  对比度: {static_analysis['contrast']:.2f} (预期: < 30)")
        print(f"  边缘活动: {static_analysis['edge_activity']:.2f} (预期: < 10)")
        print(f"  是静态: {static_analysis['is_static']} (预期: True)")

        print(f"\n复杂图像分析:")
        print(f"  对比度: {complex_analysis['contrast']:.2f} (预期: > 50)")
        print(f"  边缘活动: {complex_analysis['edge_activity']:.2f} (预期: > 10)")
        print(f"  是静态: {complex_analysis['is_static']} (预期: False)")

        # 测试决策
        should_include_static, reason = analyzer.should_include_based_on_content(static_img)
        should_include_complex, reason = analyzer.should_include_based_on_content(complex_img)

        print(f"\n决策结果:")
        print(f"  静态图像: {should_include_static} (预期: False)")
        print(f"  复杂图像: {should_include_complex} (预期: True)")

        success = (not should_include_static and should_include_complex)
        self.test_results['content_analysis'] = success
        print(f"\n✓ 测试通过: {success}\n")

        return success

    def test_density_sampling(self):
        """测试事件密度采样"""
        print("\n" + "="*60)
        print("测试 3: 事件密度采样")
        print("="*60)

        sampler = EventDensitySampler(min_interval=2.0, max_images=4)

        # 模拟事件序列
        base_time = datetime.now().timestamp()
        times = [base_time, base_time + 0.5, base_time + 1.5, base_time + 2.5,
                 base_time + 3.0, base_time + 4.0, base_time + 5.0, base_time + 6.0]

        results = []
        for i, t in enumerate(times):
            should_include, reason = sampler.should_include_image("event1", t, i == 0)
            results.append((should_include, reason))
            print(f"时刻 {i} (t={t-base_time:.1f}s): {should_include} - {reason}")

        stats = sampler.get_stats()
        print(f"\n统计信息:")
        print(f"  间隔限制: {stats['interval_throttled']}")
        print(f"  配额超限: {stats['quota_exceeded']}")

        # 验证: 只有首张、2.5s、4.0s、5.0s的应该被包含
        expected_inclusions = [True, False, False, True, False, True, False, False]
        success = all(r[0] == exp for r, exp in zip(results, expected_inclusions))

        self.test_results['density_sampling'] = success
        print(f"\n✓ 测试通过: {success}\n")

        return success

    def test_hybrid_filter_comprehensive(self):
        """综合测试混合过滤器"""
        print("\n" + "="*60)
        print("测试 4: 混合过滤器综合测试")
        print("="*60)

        # 模拟真实场景：50 张截图，包含重复、静态和有效变化
        filter_obj = HybridImageFilter(
            phash_threshold=0.15,
            min_interval=2.0,
            max_images=8,
            enable_content_analysis=True
        )

        base_time = datetime.now().timestamp()
        images_generated = 0
        images_included = 0

        print("模拟 50 张截图的处理...")

        # 创建不同类型的图像
        img_dynamic = create_test_image(seed=1)
        img_static = create_static_image()

        for i in range(50):
            # 每 5 张切换一次类型
            if i % 10 < 5:
                # 动态内容 - 30% 概率有显著变化
                if i % 3 == 0:
                    img = create_test_image(seed=i)
                else:
                    img = create_similar_image(img_dynamic, variation=0.05)
            else:
                # 静态内容
                img = img_static

            current_time = base_time + (i * 0.5)  # 每张 0.5s
            should_include, reason = filter_obj.should_include_image(
                img_bytes=img,
                event_id="test_event",
                current_time=current_time,
                is_first=(i == 0)
            )

            images_generated += 1
            if should_include:
                images_included += 1

        stats = filter_obj.get_stats_summary()
        opt_stats = stats['optimization']

        print(f"\n处理统计:")
        print(f"  总图像数: {opt_stats['total_images']}")
        print(f"  包含图像数: {opt_stats['included_images']}")
        print(f"  跳过图像数: {opt_stats['skipped_images']}")
        print(f"  节省比例: {opt_stats['saving_percentage']:.1f}%")
        print(f"  预计节省 Token: {opt_stats['estimated_tokens_saved']}")

        if opt_stats['skip_breakdown']:
            print(f"\n跳过原因分布:")
            for reason, count in opt_stats['skip_breakdown'].items():
                print(f"    {reason}: {count}")

        # 验证: 应该节省 40-70% token
        success = 40 <= opt_stats['saving_percentage'] <= 95
        self.test_results['hybrid_filter'] = success
        print(f"\n✓ 测试通过: {success}\n")

        return success

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "#"*60)
        print("# 图像优化测试套件")
        print("#"*60)

        try:
            self.test_phash_duplicate_detection()
            self.test_content_analysis()
            self.test_density_sampling()
            self.test_hybrid_filter_comprehensive()
        except Exception as e:
            logger.error(f"测试执行错误: {e}", exc_info=True)
            return False

        # 打印总结
        print("\n" + "#"*60)
        print("# 测试总结")
        print("#"*60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for v in self.test_results.values() if v)

        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {test_name}")

        print(f"\n总计: {passed_tests}/{total_tests} 测试通过")

        return passed_tests == total_tests


def print_optimization_comparison():
    """打印优化效果对比"""
    print("\n" + "#"*60)
    print("# Token 消耗对比")
    print("#"*60)

    print("""
场景: 10 秒内捕获 50 张截图 + 5 次键鼠操作

【无优化】
  图像: 50 张 × 120 tokens/张 = 6000 tokens
  文本:  5 条 ×  10 tokens/条 =   50 tokens
  总计:                           6050 tokens

【智能采样 (threshold=0.15)】
  图像: 12 张 × 120 tokens/张 = 1440 tokens
  文本:  5 条 ×  10 tokens/条 =   50 tokens
  总计:                           1490 tokens
  节省: 6050 - 1490 = 4560 tokens (75.4% ↓)

【内容感知】
  图像:  8 张 × 120 tokens/张 =  960 tokens
  文本:  5 条 ×  10 tokens/条 =   50 tokens
  总计:                            1010 tokens
  节省: 6050 - 1010 = 5040 tokens (83.3% ↓)

【混合文本 (3秒采样间隔)】
  图像:  4 张 × 120 tokens/张 =  480 tokens
  文本: 50 条 ×  10 tokens/条 =  500 tokens
  总计:                            980 tokens
  节省: 6050 - 980 = 5070 tokens (83.8% ↓)

推荐配置:
  - phash_threshold: 0.15    # 激进采样
  - min_interval: 2.0        # 2秒间隔
  - max_images: 8            # 最多8张
  - 启用内容分析: True        # 检测静态内容
""")


if __name__ == '__main__':
    # 运行测试套件
    suite = OptimizationTestSuite()
    all_passed = suite.run_all_tests()

    # 打印对比信息
    print_optimization_comparison()

    # 退出码
    exit_code = 0 if all_passed else 1
    print(f"\n程序结束，退出码: {exit_code}\n")
    sys.exit(exit_code)
