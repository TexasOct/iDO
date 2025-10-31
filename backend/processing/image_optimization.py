"""
图像优化模块 - 减少 LLM Token 消耗

提供多种优化策略：
1. 智能采样 - 基于感知哈希检测图像变化
2. 内容感知 - 检测图像内容类型和复杂度
3. 事件密度采样 - 基于时间间隔的采样
"""

import io
import numpy as np
from typing import Optional, Dict, Any, Tuple
from PIL import Image
from core.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


class ImageDifferenceAnalyzer:
    """图像变化分析器 - 使用感知哈希 (perceptual hash) 检测相似度"""

    def __init__(self, threshold: float = 0.15):
        """
        Args:
            threshold: 变化程度阈值 (0-1)，超过此值认为有显著变化
                      低阈值 = 更激进采样，更节省 token
                      高阈值 = 更保守采样，保留更多细节
        """
        self.threshold = threshold
        self.last_phash = None
        self.stats = {
            'total_checked': 0,
            'significant_changes': 0,
            'duplicates_skipped': 0
        }

    def calculate_phash(self, img_bytes: bytes) -> Optional[str]:
        """
        计算感知哈希 (Perceptual Hash)

        对相似但不完全相同的图像返回相同/相似的 hash
        比直接的 MD5 hash 更适合图像去重

        Args:
            img_bytes: 图像字节数据

        Returns:
            64 位的二进制字符串表示的 hash，或 None 如果失败
        """
        try:
            img = Image.open(io.BytesIO(img_bytes))
            # 缩小到 8×8 便于计算，保留重要的亮度信息
            img = img.resize((8, 8), Image.Resampling.LANCZOS)
            # 转灰度图便于比较
            pixels = list(img.convert('L').getdata())

            # 计算平均亮度
            avg = sum(pixels) / len(pixels)

            # 生成二进制字符串：亮度大于平均值为 1，否则为 0
            bits = ''.join(['1' if p > avg else '0' for p in pixels])
            return bits
        except Exception as e:
            logger.warning(f"计算感知哈希失败: {e}")
            return None

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        计算汉明距离 - 两个二进制字符串的不同位数

        Args:
            hash1, hash2: 64 位二进制字符串

        Returns:
            不同的位数 (0-64)
        """
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return 64  # 最大距离，认为完全不同
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    def is_significant_change(self, img_bytes: bytes) -> bool:
        """
        判断是否有显著变化

        Returns:
            True: 图像有显著变化，应该发送给 LLM
            False: 图像变化不大，可以跳过
        """
        self.stats['total_checked'] += 1

        current_phash = self.calculate_phash(img_bytes)
        if current_phash is None:
            # 哈希计算失败时，默认认为有变化（保守策略）
            logger.warning("感知哈希计算失败，默认视为有变化")
            self.stats['significant_changes'] += 1
            self.last_phash = None
            return True

        # 首张图像总是认为有变化
        if self.last_phash is None:
            self.last_phash = current_phash
            self.stats['significant_changes'] += 1
            return True

        # 计算相似度 (0-1, 1 表示完全相同)
        distance = self.hamming_distance(self.last_phash, current_phash)
        similarity = 1 - (distance / 64.0)

        # 判断变化是否超过阈值
        has_change = similarity < (1 - self.threshold)

        if has_change:
            self.last_phash = current_phash
            self.stats['significant_changes'] += 1
        else:
            self.stats['duplicates_skipped'] += 1

        return has_change

    def reset(self):
        """重置状态，用于处理新的事件序列"""
        self.last_phash = None
        self.stats = {
            'total_checked': 0,
            'significant_changes': 0,
            'duplicates_skipped': 0
        }

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()


class ImageContentAnalyzer:
    """图像内容分析器 - 检测图像内容类型和复杂度"""

    def __init__(self):
        self.stats = {
            'static_skipped': 0,
            'high_contrast_included': 0,
            'motion_detected': 0
        }

    def analyze_content(self, img_bytes: bytes) -> Dict[str, Any]:
        """
        分析图像内容特征

        Returns:
            包含以下字段的字典：
            - contrast: 对比度 (0-255)
            - edge_activity: 边缘活动程度
            - is_static: 是否为静态内容
            - has_motion: 是否检测到运动
        """
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert('L')
            pixels = np.array(img, dtype=np.float32)

            # 计算对比度 (标准差)
            contrast = float(np.std(pixels))

            # 计算边缘活动
            if pixels.size > 1:
                edges = np.abs(np.diff(pixels.flatten()))
                edge_activity = float(np.mean(edges))
            else:
                edge_activity = 0.0

            # 判断特征
            is_static = contrast < 30  # 低对比度
            has_motion = edge_activity > 10  # 高边缘活动

            return {
                'contrast': contrast,
                'edge_activity': edge_activity,
                'is_static': is_static,
                'has_motion': has_motion
            }
        except Exception as e:
            logger.warning(f"内容分析失败: {e}")
            return {
                'contrast': 0,
                'edge_activity': 0,
                'is_static': False,
                'has_motion': False
            }

    def should_include_based_on_content(self, img_bytes: bytes) -> Tuple[bool, str]:
        """
        基于内容判断是否应该发送给 LLM

        Returns:
            (should_include, reason)
        """
        content = self.analyze_content(img_bytes)

        # 规则1: 高对比度 = 可能是有意义的界面变化
        if content['contrast'] > 50:
            self.stats['high_contrast_included'] += 1
            return True, "高对比度内容"

        # 规则2: 检测到运动 = 用户在交互
        if content['has_motion']:
            self.stats['motion_detected'] += 1
            return True, "检测到运动"

        # 规则3: 低对比度且无运动 = 可能是空白/等待屏幕
        if content['is_static'] and content['contrast'] < 20:
            self.stats['static_skipped'] += 1
            return False, "静态/空白内容"

        return True, "中等复杂度"

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()


class EventDensitySampler:
    """基于事件密度的采样器 - 根据时间和数量限制采样"""

    def __init__(self, min_interval: float = 2.0, max_images: int = 8):
        """
        Args:
            min_interval: 两张图像之间的最小间隔（秒）
            max_images: 单个事件序列最多采样的图像数
        """
        self.min_interval = min_interval
        self.max_images = max_images
        self.last_sampled_time = {}
        self.images_count = {}
        self.stats = {
            'interval_throttled': 0,
            'quota_exceeded': 0
        }

    def should_include_image(self,
                            event_id: str,
                            current_time: float,
                            is_significant_change: bool) -> Tuple[bool, str]:
        """
        判断是否应该包含这张图像

        Args:
            event_id: 事件 ID（用于追踪）
            current_time: 当前时间戳
            is_significant_change: 是否是显著变化

        Returns:
            (should_include, reason)
        """
        # 规则1: 如果有显著变化，总是包含
        if is_significant_change:
            current_count = self.images_count.get(event_id, 0)

            # 但需要检查是否超过配额
            if current_count >= self.max_images:
                self.stats['quota_exceeded'] += 1
                return False, f"已达到上限 ({self.max_images})"

            self.last_sampled_time[event_id] = current_time
            self.images_count[event_id] = current_count + 1
            return True, "显著变化"

        # 规则2: 检查时间间隔
        last_time = self.last_sampled_time.get(event_id, 0)
        if current_time - last_time >= self.min_interval:
            current_count = self.images_count.get(event_id, 0)

            # 同时检查配额
            if current_count >= self.max_images:
                self.stats['quota_exceeded'] += 1
                return False, f"已达到上限 ({self.max_images})"

            self.last_sampled_time[event_id] = current_time
            self.images_count[event_id] = current_count + 1
            return True, f"时间间隔 {current_time - last_time:.1f}s"

        # 规则3: 时间间隔不足
        self.stats['interval_throttled'] += 1
        return False, f"间隔不足 {self.min_interval}s"

    def reset(self):
        """重置状态，用于处理新的事件序列"""
        self.last_sampled_time = {}
        self.images_count = {}
        self.stats = {
            'interval_throttled': 0,
            'quota_exceeded': 0
        }

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()


class ImageOptimizationStats:
    """图像优化统计追踪器"""

    def __init__(self):
        self.total_images = 0
        self.included_images = 0
        self.skipped_images = 0
        self.skip_reasons = {}
        self.start_time = datetime.now()

    def record_image(self, included: bool, reason: str = ""):
        """记录一张图像的处理结果"""
        self.total_images += 1
        if included:
            self.included_images += 1
        else:
            self.skipped_images += 1
            self.skip_reasons[reason] = self.skip_reasons.get(reason, 0) + 1

    def get_summary(self) -> Dict[str, Any]:
        """获取优化统计摘要"""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if self.total_images == 0:
            return {
                'total_images': 0,
                'included_images': 0,
                'skipped_images': 0,
                'saving_percentage': 0.0,
                'estimated_tokens_saved': 0,
                'skip_breakdown': {}
            }

        saving_pct = (self.skipped_images / self.total_images) * 100
        # 假设每张压缩图像约 120 tokens
        tokens_per_image = 120
        estimated_saved = self.skipped_images * tokens_per_image

        return {
            'total_images': self.total_images,
            'included_images': self.included_images,
            'skipped_images': self.skipped_images,
            'saving_percentage': round(saving_pct, 1),
            'estimated_tokens_saved': estimated_saved,
            'skip_breakdown': self.skip_reasons.copy(),
            'elapsed_seconds': round(elapsed, 2)
        }

    def log_summary(self):
        """记录优化统计摘要"""
        summary = self.get_summary()
        if summary['total_images'] > 0:
            logger.info(
                f"图像优化统计: "
                f"总计 {summary['total_images']}, "
                f"包含 {summary['included_images']}, "
                f"跳过 {summary['skipped_images']} "
                f"({summary['saving_percentage']:.1f}%), "
                f"预计节省 {summary['estimated_tokens_saved']} tokens"
            )

            if summary['skip_breakdown']:
                logger.debug(f"跳过原因分布: {summary['skip_breakdown']}")


class HybridImageFilter:
    """
    混合图像过滤器 - 综合使用多种优化策略

    组合使用：
    1. 感知哈希检测变化
    2. 内容分析筛选
    3. 时间/数量限制
    """

    def __init__(self,
                 phash_threshold: float = 0.15,
                 min_interval: float = 2.0,
                 max_images: int = 8,
                 enable_content_analysis: bool = True):
        """
        Args:
            phash_threshold: 感知哈希变化阈值
            min_interval: 最小采样间隔（秒）
            max_images: 最多采样图像数
            enable_content_analysis: 是否启用内容分析
        """
        self.diff_analyzer = ImageDifferenceAnalyzer(threshold=phash_threshold)
        self.content_analyzer = ImageContentAnalyzer() if enable_content_analysis else None
        self.sampler = EventDensitySampler(min_interval=min_interval, max_images=max_images)
        self.stats = ImageOptimizationStats()
        self.enable_content_analysis = enable_content_analysis

    def should_include_image(self,
                            img_bytes: bytes,
                            event_id: str,
                            current_time: float,
                            is_first: bool = False) -> Tuple[bool, str]:
        """
        综合判断是否应该包含这张图像

        Returns:
            (should_include, reason)
        """
        # 规则1: 首张图像总是包含
        if is_first:
            self.stats.record_image(True, "首张")
            return True, "首张图像"

        # 规则2: 检测重复 (感知哈希)
        if not self.diff_analyzer.is_significant_change(img_bytes):
            self.stats.record_image(False, "重复")
            return False, "与前一张重复"

        # 规则3: 内容分析（可选）
        if self.enable_content_analysis and self.content_analyzer:
            should_include, content_reason = \
                self.content_analyzer.should_include_based_on_content(img_bytes)
            if not should_include:
                self.stats.record_image(False, content_reason)
                return False, content_reason

        # 规则4: 时间/数量限制
        should_include, sampler_reason = \
            self.sampler.should_include_image(event_id, current_time, True)

        self.stats.record_image(should_include, sampler_reason if not should_include else "")
        return should_include, sampler_reason

    def reset(self):
        """重置状态，用于处理新的事件序列"""
        self.diff_analyzer.reset()
        self.sampler.reset()

    def get_stats_summary(self) -> Dict[str, Any]:
        """获取完整的统计摘要"""
        return {
            'optimization': self.stats.get_summary(),
            'diff_analyzer': self.diff_analyzer.get_stats(),
            'content_analyzer': self.content_analyzer.get_stats() if self.content_analyzer else {},
            'sampler': self.sampler.get_stats()
        }

    def log_summary(self):
        """记录统计摘要"""
        self.stats.log_summary()


# 全局单例
_global_image_filter: Optional[HybridImageFilter] = None


def get_image_filter(reset: bool = False) -> HybridImageFilter:
    """获取或创建全局图像过滤器实例"""
    global _global_image_filter

    if _global_image_filter is None or reset:
        # 从配置读取参数（如果可用）
        try:
            from core.settings import get_settings
            settings = get_settings()
            config = settings.get_image_optimization_config()

            _global_image_filter = HybridImageFilter(
                phash_threshold=config.get('phash_threshold', 0.15),
                min_interval=config.get('min_interval', 2.0),
                max_images=config.get('max_images', 8),
                enable_content_analysis=config.get('enable_content_analysis', True)
            )
            logger.info(f"图像过滤器已初始化: {config}")
        except Exception as e:
            logger.debug(f"从配置读取图像优化参数失败: {e}，使用默认参数")
            _global_image_filter = HybridImageFilter()

    return _global_image_filter
