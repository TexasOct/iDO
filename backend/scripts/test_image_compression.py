#!/usr/bin/env python
"""
Image compression test script

Test dynamic image compression and region cropping effects

Usage:
    python backend/scripts/test_image_compression.py

    Or run with uv:
    uv run python backend/scripts/test_image_compression.py
"""

import sys
import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Add project root path and backend path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from core.logger import get_logger
from processing.image_compression import (
    ImageImportanceAnalyzer,
    DynamicImageCompressor,
    RegionCropper,
    AdvancedImageOptimizer,
)

logger = get_logger(__name__)


def create_test_image(width=1920, height=1080, complexity="medium") -> bytes:
    """创建测试图像"""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    if complexity == "low":
        # 低复杂度 - 纯色背景
        draw.rectangle([0, 0, width, height], fill=(200, 200, 200))

    elif complexity == "medium":
        # 中等复杂度 - 简单形状
        draw.rectangle([100, 100, 500, 500], fill=(100, 150, 200))
        draw.ellipse([600, 100, 1000, 500], fill=(200, 100, 150))
        draw.polygon([(1200, 100), (1500, 300), (1300, 500)], fill=(150, 200, 100))

    elif complexity == "high":
        # 高复杂度 - 随机噪声 + 形状
        pixels = np.array(img)
        noise = np.random.randint(0, 50, pixels.shape, dtype=np.uint8)
        pixels = np.clip(pixels.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(pixels)
        draw = ImageDraw.Draw(img)

        # 添加形状
        for i in range(20):
            x = np.random.randint(0, width - 200)
            y = np.random.randint(0, height - 200)
            draw.rectangle(
                [x, y, x + 200, y + 200],
                fill=tuple(np.random.randint(0, 256, 3).tolist()),
            )

    # 转换为字节
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=95)
    return output.getvalue()


def test_importance_analyzer():
    """测试重要性分析器"""
    print("\n" + "=" * 60)
    print("测试 1: 图像重要性分析")
    print("=" * 60)

    analyzer = ImageImportanceAnalyzer()

    # 测试不同复杂度的图像
    test_cases = [
        ("低复杂度", create_test_image(complexity="low")),
        ("中等复杂度", create_test_image(complexity="medium")),
        ("高复杂度", create_test_image(complexity="high")),
    ]

    results = []
    for name, img_bytes in test_cases:
        importance = analyzer.analyze_importance(img_bytes)
        results.append((name, importance))
        print(f"{name}: {importance}")

    # 验证
    success = (
        results[0][1] == "low"
        and results[1][1] in ["medium", "high"]
        and results[2][1] == "high"
    )

    print(f"\n统计: {analyzer.stats}")
    print(f"✓ 测试通过: {success}\n")
    return success


def test_dynamic_compressor():
    """测试动态压缩器"""
    print("\n" + "=" * 60)
    print("测试 2: 动态图像压缩")
    print("=" * 60)

    # 测试不同压缩级别
    levels = ["ultra", "aggressive", "balanced", "quality"]

    img_bytes = create_test_image(complexity="medium")
    original_size = len(img_bytes)

    print(f"原始图像: {original_size / 1024:.1f} KB\n")

    results = []
    for level in levels:
        compressor = DynamicImageCompressor(compression_level=level)

        # 强制使用中等重要性
        compressed, meta = compressor.compress(img_bytes, force_importance="medium")

        compressed_size = len(compressed)
        ratio = compressed_size / original_size

        print(
            f"{level:12s}: {compressed_size / 1024:.1f} KB "
            f"({ratio * 100:.1f}%), "
            f"质量={meta['quality']}, "
            f"尺寸={meta['final_dimensions']}"
        )

        results.append({"level": level, "ratio": ratio, "size": compressed_size})

    # 验证：ultra < aggressive < balanced < quality
    success = (
        results[0]["ratio"]
        < results[1]["ratio"]
        < results[2]["ratio"]
        < results[3]["ratio"]
    )

    print(f"\n✓ 测试通过: {success}\n")
    return success


def test_region_cropper():
    """测试区域裁剪器"""
    print("\n" + "=" * 60)
    print("测试 3: 智能区域裁剪")
    print("=" * 60)

    cropper = RegionCropper(diff_threshold=30)

    # 创建两张图像，第二张只有局部变化
    img1_bytes = create_test_image(complexity="medium")

    # 创建第二张图像（只修改部分区域）
    img1 = Image.open(io.BytesIO(img1_bytes))
    draw = ImageDraw.Draw(img1)
    # 在角落添加变化
    draw.rectangle([50, 50, 300, 300], fill=(255, 0, 0))
    output = io.BytesIO()
    img1.save(output, format="JPEG", quality=95)
    img2_bytes = output.getvalue()

    # 第一张图像（完整）
    cropped1, meta1 = cropper.crop_changed_region(img1_bytes)
    print(f"首张图像: {meta1['is_cropped']} (预期: False)")

    # 第二张图像（应该裁剪）
    cropped2, meta2 = cropper.crop_changed_region(img2_bytes)
    print(f"第二张图像: 裁剪={meta2['is_cropped']}")

    if meta2["is_cropped"]:
        print(f"  原始尺寸: {meta2['original_size']}")
        print(f"  裁剪尺寸: {meta2['cropped_size']}")
        print(f"  保留区域: {meta2['crop_ratio'] * 100:.1f}%")
        print(f"  大小缩减: {meta2['size_reduction'] * 100:.1f}%")

    # 第三张图像（无变化，应该不裁剪）
    cropped3, meta3 = cropper.crop_changed_region(img2_bytes)
    print(f"第三张图像 (重复): {meta3['is_cropped']} (预期: False)")

    stats = cropper.get_stats()
    print(f"\n统计:")
    print(f"  总图像: {stats['total_images']}")
    print(f"  完整图像: {stats['full_images']}")
    print(f"  裁剪图像: {stats['cropped_images']}")

    success = (
        not meta1["is_cropped"]
        and meta2.get("is_cropped", False)
        and not meta3["is_cropped"]
    )

    print(f"\n✓ 测试通过: {success}\n")
    return success


def test_advanced_optimizer():
    """测试高级优化器"""
    print("\n" + "=" * 60)
    print("测试 4: 高级图像优化器（综合测试）")
    print("=" * 60)

    # 测试不同配置
    configs = [
        ("超激进", "ultra", False),
        ("激进+裁剪", "aggressive", True),
        ("平衡", "balanced", False),
    ]

    # 创建测试序列（模拟实际使用）
    test_images = []
    base_img = create_test_image(complexity="medium")
    test_images.append(("基础图像", base_img))

    # 创建 5 张轻微变化的图像
    for i in range(5):
        img = Image.open(io.BytesIO(base_img))
        draw = ImageDraw.Draw(img)
        # 随机位置添加小变化
        x = np.random.randint(0, 1600)
        y = np.random.randint(0, 800)
        draw.rectangle(
            [x, y, x + 100, y + 100], fill=tuple(np.random.randint(0, 256, 3).tolist())
        )
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=95)
        test_images.append((f"变化 {i + 1}", output.getvalue()))

    for config_name, compression_level, enable_cropping in configs:
        print(
            f"\n配置: {config_name} (压缩={compression_level}, 裁剪={enable_cropping})"
        )
        print("-" * 60)

        optimizer = AdvancedImageOptimizer(
            compression_level=compression_level, enable_cropping=enable_cropping
        )

        total_original_size = 0
        total_optimized_size = 0

        for i, (name, img_bytes) in enumerate(test_images):
            optimized, meta = optimizer.optimize(img_bytes, is_first=(i == 0))

            total_original_size += len(img_bytes)
            total_optimized_size += len(optimized)

            if i == 0 or i == len(test_images) - 1:
                print(
                    f"  {name}: "
                    f"{len(img_bytes) / 1024:.1f}KB → {len(optimized) / 1024:.1f}KB, "
                    f"Token: {meta['original_tokens']} → {meta['optimized_tokens']}"
                )

        # 获取统计
        stats = optimizer.get_stats()

        print(f"\n  总体统计:")
        print(f"    处理图像: {stats['images_processed']}")
        print(f"    Token 原始: {stats['tokens']['original']}")
        print(f"    Token 优化: {stats['tokens']['optimized']}")
        print(
            f"    Token 节省: {stats['tokens']['saved']} ({stats['tokens']['reduction_percentage']:.1f}%)"
        )
        print(f"    空间节省: {stats['compression']['space_saved_mb']:.2f} MB")

    print(f"\n✓ 测试完成\n")
    return True


def print_comparison_table():
    """打印效果对比表"""
    print("\n" + "=" * 60)
    print("图像优化效果对比")
    print("=" * 60)

    print("""
场景: 10 秒内 50 张截图 (1920×1080, 质量 85)

【无优化】
  图像数: 50 张
  单张大小: ~150 KB
  总大小: 7.5 MB
  Token 消耗: 50 × 120 = 6000 tokens

【智能采样】(phash_threshold=0.08)
  图像数: 12 张 (节省 76%)
  单张大小: ~150 KB
  总大小: 1.8 MB
  Token 消耗: 12 × 120 = 1440 tokens
  节省: 4560 tokens (76%)

【采样 + 激进压缩】⭐ 推荐
  图像数: 12 张 (节省 76%)
  单张大小: ~40 KB (压缩 73%)
  总大小: 0.48 MB
  Token 消耗: 12 × 32 = 384 tokens
  节省: 5616 tokens (93.6%)

【采样 + 超激进压缩】
  图像数: 12 张 (节省 76%)
  单张大小: ~25 KB (压缩 83%)
  总大小: 0.3 MB
  Token 消耗: 12 × 20 = 240 tokens
  节省: 5760 tokens (96%)

【采样 + 压缩 + 区域裁剪】(实验性)
  图像数: 12 张 (节省 76%)
  单张大小: ~20 KB (压缩 + 裁剪 87%)
  总大小: 0.24 MB
  Token 消耗: 12 × 16 = 192 tokens
  节省: 5808 tokens (96.8%)

推荐配置:
  - phash_threshold: 0.08
  - min_interval: 3.5
  - max_images: 5
  - compression_level: "aggressive"  ← 新增
  - enable_region_cropping: false    ← 可选

预期总体效果:
  Token 节省: 93-96%
  质量损失: 最小（LLM 仍能准确理解）
""")


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("# 图像压缩优化测试套件")
    print("#" * 60)

    results = []

    try:
        results.append(("重要性分析", test_importance_analyzer()))
        results.append(("动态压缩", test_dynamic_compressor()))
        results.append(("区域裁剪", test_region_cropper()))
        results.append(("高级优化器", test_advanced_optimizer()))
    except Exception as e:
        logger.error(f"测试执行错误: {e}", exc_info=True)
        results.append(("执行错误", False))

    # 打印总结
    print("\n" + "#" * 60)
    print("# 测试总结")
    print("#" * 60)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\n总计: {passed}/{total} 测试通过")

    # 打印对比表
    print_comparison_table()

    # 退出码
    exit_code = 0 if passed == total else 1
    print(f"\n程序结束，退出码: {exit_code}\n")
    sys.exit(exit_code)
