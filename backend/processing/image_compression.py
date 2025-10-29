"""
高级图像压缩模块 - 进一步减少图像大小和 Token 消耗

实现策略：
1. 动态质量调整 - 根据内容重要性动态调整 JPEG 质量
2. 自适应分辨率 - 根据图像复杂度调整分辨率
3. 智能区域裁剪 - 只保留有变化的区域
4. 多级降级策略 - 为不同场景提供不同压缩级别
"""

import io
import base64
import numpy as np
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageFilter
from core.logger import get_logger

logger = get_logger(__name__)


class ImageImportanceAnalyzer:
    """图像重要性分析器 - 判断图像的信息密度和重要性"""

    def __init__(self):
        self.stats = {
            'high_importance': 0,
            'medium_importance': 0,
            'low_importance': 0
        }

    def analyze_importance(self, img_bytes: bytes) -> str:
        """
        分析图像重要性

        Returns:
            'high', 'medium', 'low'
        """
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')

            # 计算多个指标
            contrast = self._calculate_contrast(img)
            complexity = self._calculate_complexity(img)
            edge_density = self._calculate_edge_density(img)

            # 综合评分 (0-100)
            score = (
                contrast * 0.4 +
                complexity * 0.3 +
                edge_density * 0.3
            )

            # 分级
            if score > 60:
                self.stats['high_importance'] += 1
                return 'high'
            elif score > 30:
                self.stats['medium_importance'] += 1
                return 'medium'
            else:
                self.stats['low_importance'] += 1
                return 'low'

        except Exception as e:
            logger.warning(f"分析图像重要性失败: {e}")
            return 'medium'  # 默认中等

    def _calculate_contrast(self, img: Image.Image) -> float:
        """计算对比度 (0-100)"""
        gray = img.convert('L')
        pixels = np.array(gray, dtype=np.float32)
        std = float(np.std(pixels))
        # 归一化到 0-100
        return min(100, std / 2.55)

    def _calculate_complexity(self, img: Image.Image) -> float:
        """计算图像复杂度 (0-100)，基于颜色变化"""
        small = img.resize((32, 32), Image.Resampling.LANCZOS)
        pixels = np.array(small, dtype=np.float32)

        # 计算像素间差异
        diff_h = np.abs(np.diff(pixels, axis=0)).mean()
        diff_v = np.abs(np.diff(pixels, axis=1)).mean()

        complexity = (diff_h + diff_v) / 2
        # 归一化到 0-100
        return min(100, complexity / 2.55)

    def _calculate_edge_density(self, img: Image.Image) -> float:
        """计算边缘密度 (0-100)"""
        gray = img.convert('L')
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_pixels = np.array(edges, dtype=np.float32)

        # 边缘像素占比
        edge_ratio = (edge_pixels > 50).sum() / edge_pixels.size

        # 归一化到 0-100
        return min(100, edge_ratio * 500)


class DynamicImageCompressor:
    """动态图像压缩器 - 根据重要性调整压缩参数"""

    # 压缩级别定义
    COMPRESSION_LEVELS = {
        'ultra': {
            'high': {'quality': 50, 'max_size': (600, 400), 'description': '超激进'},
            'medium': {'quality': 40, 'max_size': (480, 320), 'description': '超激进'},
            'low': {'quality': 30, 'max_size': (400, 300), 'description': '超激进'}
        },
        'aggressive': {
            'high': {'quality': 60, 'max_size': (800, 600), 'description': '激进'},
            'medium': {'quality': 50, 'max_size': (640, 480), 'description': '激进'},
            'low': {'quality': 40, 'max_size': (480, 360), 'description': '激进'}
        },
        'balanced': {
            'high': {'quality': 75, 'max_size': (1280, 720), 'description': '平衡'},
            'medium': {'quality': 65, 'max_size': (960, 540), 'description': '平衡'},
            'low': {'quality': 55, 'max_size': (800, 450), 'description': '平衡'}
        },
        'quality': {
            'high': {'quality': 85, 'max_size': (1920, 1080), 'description': '质量优先'},
            'medium': {'quality': 80, 'max_size': (1600, 900), 'description': '质量优先'},
            'low': {'quality': 75, 'max_size': (1280, 720), 'description': '质量优先'}
        }
    }

    def __init__(self, compression_level: str = 'aggressive'):
        """
        Args:
            compression_level: 'ultra', 'aggressive', 'balanced', 'quality'
        """
        self.compression_level = compression_level
        self.importance_analyzer = ImageImportanceAnalyzer()
        self.stats = {
            'original_size': 0,
            'compressed_size': 0,
            'compression_ratio': 0.0,
            'images_processed': 0
        }

    def compress(self, img_bytes: bytes, force_importance: Optional[str] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        压缩图像

        Args:
            img_bytes: 原始图像字节
            force_importance: 强制指定重要性等级（可选）

        Returns:
            (compressed_bytes, metadata)
        """
        try:
            original_size = len(img_bytes)
            self.stats['original_size'] += original_size
            self.stats['images_processed'] += 1

            # 分析重要性
            importance = force_importance or self.importance_analyzer.analyze_importance(img_bytes)

            # 获取压缩参数
            params = self.COMPRESSION_LEVELS[self.compression_level][importance]
            quality = params['quality']
            max_size = params['max_size']

            # 打开图像
            img = Image.open(io.BytesIO(img_bytes))
            original_dimensions = img.size

            # 调整分辨率
            img = self._resize_smart(img, max_size)

            # 转换颜色空间优化
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # 压缩
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            compressed_bytes = output.getvalue()

            compressed_size = len(compressed_bytes)
            self.stats['compressed_size'] += compressed_size

            # 计算压缩比
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0

            metadata = {
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'size_reduction': 1 - compression_ratio,
                'original_dimensions': original_dimensions,
                'final_dimensions': img.size,
                'quality': quality,
                'importance': importance,
                'compression_level': self.compression_level
            }

            logger.debug(
                f"图像压缩: {original_dimensions[0]}x{original_dimensions[1]} → "
                f"{img.size[0]}x{img.size[1]}, "
                f"{original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB "
                f"({compression_ratio*100:.1f}%), "
                f"重要性: {importance}, 质量: {quality}"
            )

            return compressed_bytes, metadata

        except Exception as e:
            logger.error(f"图像压缩失败: {e}")
            # 失败时返回原图
            return img_bytes, {
                'error': str(e),
                'compression_ratio': 1.0
            }

    def _resize_smart(self, img: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
        """
        智能调整图像尺寸，保持宽高比

        Args:
            img: PIL Image
            max_size: (max_width, max_height)

        Returns:
            调整后的图像
        """
        width, height = img.size
        max_width, max_height = max_size

        # 如果已经小于目标尺寸，不调整
        if width <= max_width and height <= max_height:
            return img

        # 计算缩放比例，保持宽高比
        ratio_w = max_width / width
        ratio_h = max_height / height
        ratio = min(ratio_w, ratio_h)

        new_width = int(width * ratio)
        new_height = int(height * ratio)

        # 使用 LANCZOS 保证质量
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def get_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        if self.stats['original_size'] > 0:
            overall_ratio = self.stats['compressed_size'] / self.stats['original_size']
        else:
            overall_ratio = 1.0

        return {
            'images_processed': self.stats['images_processed'],
            'total_original_size_mb': self.stats['original_size'] / (1024 * 1024),
            'total_compressed_size_mb': self.stats['compressed_size'] / (1024 * 1024),
            'overall_compression_ratio': overall_ratio,
            'overall_size_reduction': 1 - overall_ratio,
            'space_saved_mb': (self.stats['original_size'] - self.stats['compressed_size']) / (1024 * 1024),
            'importance_distribution': self.importance_analyzer.stats
        }


class RegionCropper:
    """智能区域裁剪器 - 只保留有变化的区域"""

    def __init__(self, diff_threshold: int = 30, min_region_size: int = 100):
        """
        Args:
            diff_threshold: 像素差异阈值（0-255）
            min_region_size: 最小区域尺寸（像素）
        """
        self.diff_threshold = diff_threshold
        self.min_region_size = min_region_size
        self.last_image = None
        self.stats = {
            'full_images': 0,
            'cropped_images': 0,
            'total_crop_ratio': 0.0
        }

    def crop_changed_region(self, img_bytes: bytes, force_full: bool = False) -> Tuple[bytes, Dict[str, Any]]:
        """
        裁剪只包含变化的区域

        Args:
            img_bytes: 当前图像字节
            force_full: 强制返回完整图像

        Returns:
            (cropped_bytes, metadata)
        """
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')

            # 首张图像或强制完整
            if self.last_image is None or force_full:
                self.last_image = img
                self.stats['full_images'] += 1

                return img_bytes, {
                    'is_cropped': False,
                    'crop_ratio': 1.0,
                    'reason': 'first_image' if self.last_image is None else 'forced_full'
                }

            # 计算差异
            bbox = self._find_diff_bbox(self.last_image, img)

            if bbox is None:
                # 无明显差异，返回原图
                self.stats['full_images'] += 1
                return img_bytes, {
                    'is_cropped': False,
                    'crop_ratio': 1.0,
                    'reason': 'no_significant_change'
                }

            # 裁剪变化区域
            cropped = img.crop(bbox)

            # 检查裁剪区域是否太小
            crop_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            full_area = img.width * img.height
            crop_ratio = crop_area / full_area

            if crop_ratio > 0.8:
                # 变化区域太大，保留完整图像
                self.last_image = img
                self.stats['full_images'] += 1
                return img_bytes, {
                    'is_cropped': False,
                    'crop_ratio': crop_ratio,
                    'reason': 'change_too_large'
                }

            # 保存裁剪图像
            output = io.BytesIO()
            cropped.save(output, format='JPEG', quality=85)
            cropped_bytes = output.getvalue()

            # 更新统计
            self.last_image = img
            self.stats['cropped_images'] += 1
            self.stats['total_crop_ratio'] += crop_ratio

            metadata = {
                'is_cropped': True,
                'crop_ratio': crop_ratio,
                'original_size': img.size,
                'cropped_size': cropped.size,
                'bbox': bbox,
                'size_reduction': 1 - (len(cropped_bytes) / len(img_bytes))
            }

            logger.debug(
                f"区域裁剪: {img.size[0]}x{img.size[1]} → "
                f"{cropped.size[0]}x{cropped.size[1]} "
                f"({crop_ratio*100:.1f}% 保留)"
            )

            return cropped_bytes, metadata

        except Exception as e:
            logger.error(f"区域裁剪失败: {e}")
            return img_bytes, {
                'is_cropped': False,
                'error': str(e)
            }

    def _find_diff_bbox(self, img1: Image.Image, img2: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """
        找到两张图像的差异区域边界

        Returns:
            (left, top, right, bottom) 或 None
        """
        try:
            # 确保尺寸相同
            if img1.size != img2.size:
                return None

            # 转换为 numpy 数组
            arr1 = np.array(img1, dtype=np.float32)
            arr2 = np.array(img2, dtype=np.float32)

            # 计算像素差异
            diff = np.abs(arr1 - arr2).mean(axis=2)  # 平均 RGB 差异

            # 二值化差异图
            changed = diff > self.diff_threshold

            # 找到变化区域的边界
            rows = np.any(changed, axis=1)
            cols = np.any(changed, axis=0)

            if not rows.any() or not cols.any():
                return None

            top = np.argmax(rows)
            bottom = len(rows) - np.argmax(rows[::-1])
            left = np.argmax(cols)
            right = len(cols) - np.argmax(cols[::-1])

            # 添加边距
            margin = 10
            width, height = img1.size

            left = max(0, left - margin)
            top = max(0, top - margin)
            right = min(width, right + margin)
            bottom = min(height, bottom + margin)

            # 检查区域大小
            region_width = right - left
            region_height = bottom - top

            if region_width < self.min_region_size or region_height < self.min_region_size:
                return None

            return (left, top, right, bottom)

        except Exception as e:
            logger.warning(f"计算差异边界失败: {e}")
            return None

    def reset(self):
        """重置状态"""
        self.last_image = None

    def get_stats(self) -> Dict[str, Any]:
        """获取裁剪统计"""
        total_images = self.stats['full_images'] + self.stats['cropped_images']
        avg_crop_ratio = (
            self.stats['total_crop_ratio'] / self.stats['cropped_images']
            if self.stats['cropped_images'] > 0 else 1.0
        )

        return {
            'total_images': total_images,
            'full_images': self.stats['full_images'],
            'cropped_images': self.stats['cropped_images'],
            'crop_percentage': (
                self.stats['cropped_images'] / total_images * 100
                if total_images > 0 else 0
            ),
            'average_crop_ratio': avg_crop_ratio,
            'average_size_reduction': 1 - avg_crop_ratio
        }


class AdvancedImageOptimizer:
    """
    高级图像优化器 - 综合使用压缩和裁剪

    工作流程：
    1. 分析图像重要性
    2. 根据重要性动态压缩
    3. （可选）裁剪变化区域
    4. 记录详细统计
    """

    def __init__(self,
                 compression_level: str = 'aggressive',
                 enable_cropping: bool = False,
                 crop_threshold: int = 30):
        """
        Args:
            compression_level: 压缩级别 ('ultra', 'aggressive', 'balanced', 'quality')
            enable_cropping: 是否启用区域裁剪
            crop_threshold: 裁剪差异阈值
        """
        self.compressor = DynamicImageCompressor(compression_level)
        self.cropper = RegionCropper(diff_threshold=crop_threshold) if enable_cropping else None
        self.enable_cropping = enable_cropping
        self.stats = {
            'images_processed': 0,
            'total_original_tokens': 0,
            'total_optimized_tokens': 0
        }

    def optimize(self, img_bytes: bytes, is_first: bool = False) -> Tuple[bytes, Dict[str, Any]]:
        """
        优化图像

        Args:
            img_bytes: 原始图像字节
            is_first: 是否是首张图像（首张不裁剪）

        Returns:
            (optimized_bytes, metadata)
        """
        try:
            original_size = len(img_bytes)

            # 估算原始 token 数（假设 1KB ≈ 85 tokens）
            original_tokens = int(original_size / 1024 * 85)
            self.stats['total_original_tokens'] += original_tokens

            # 第 1 步：区域裁剪（可选）
            if self.enable_cropping and self.cropper:
                img_bytes, crop_meta = self.cropper.crop_changed_region(
                    img_bytes,
                    force_full=is_first
                )
            else:
                crop_meta = {'is_cropped': False}

            # 第 2 步：动态压缩
            compressed_bytes, compress_meta = self.compressor.compress(img_bytes)

            # 估算优化后 token 数
            optimized_tokens = int(len(compressed_bytes) / 1024 * 85)
            self.stats['total_optimized_tokens'] += optimized_tokens
            self.stats['images_processed'] += 1

            # 综合元数据
            metadata = {
                'original_size': original_size,
                'final_size': len(compressed_bytes),
                'total_reduction': 1 - (len(compressed_bytes) / original_size),
                'original_tokens': original_tokens,
                'optimized_tokens': optimized_tokens,
                'tokens_saved': original_tokens - optimized_tokens,
                'cropping': crop_meta,
                'compression': compress_meta
            }

            logger.debug(
                f"图像优化完成: {original_size/1024:.1f}KB → {len(compressed_bytes)/1024:.1f}KB, "
                f"Token: {original_tokens} → {optimized_tokens} "
                f"(节省 {metadata['tokens_saved']})"
            )

            return compressed_bytes, metadata

        except Exception as e:
            logger.error(f"图像优化失败: {e}")
            return img_bytes, {
                'error': str(e),
                'total_reduction': 0
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取综合统计"""
        compression_stats = self.compressor.get_stats()
        cropping_stats = self.cropper.get_stats() if self.cropper else {}

        token_reduction = (
            1 - (self.stats['total_optimized_tokens'] / self.stats['total_original_tokens'])
            if self.stats['total_original_tokens'] > 0 else 0
        )

        return {
            'images_processed': self.stats['images_processed'],
            'tokens': {
                'original': self.stats['total_original_tokens'],
                'optimized': self.stats['total_optimized_tokens'],
                'saved': self.stats['total_original_tokens'] - self.stats['total_optimized_tokens'],
                'reduction_percentage': token_reduction * 100
            },
            'compression': compression_stats,
            'cropping': cropping_stats
        }

    def reset(self):
        """重置所有状态"""
        if self.cropper:
            self.cropper.reset()
        self.stats = {
            'images_processed': 0,
            'total_original_tokens': 0,
            'total_optimized_tokens': 0
        }

    def reinitialize(self, compression_level: str = 'aggressive',
                     enable_cropping: bool = False,
                     crop_threshold: int = 30):
        """重新初始化优化器配置（用于动态配置更新）

        Args:
            compression_level: 压缩级别
            enable_cropping: 是否启用区域裁剪
            crop_threshold: 裁剪阈值百分比
        """
        # 重新创建压缩器
        self.compressor = DynamicImageCompressor(compression_level)

        # 重新创建裁剪器（如果需要）
        if enable_cropping:
            if not self.cropper:
                self.cropper = RegionCropper(change_threshold=crop_threshold)
            else:
                self.cropper.change_threshold = crop_threshold
        else:
            self.cropper = None

        # 重置统计数据
        self.reset()

        logger.info(f"图像优化器已重新初始化: level={compression_level}, cropping={enable_cropping}")


# 全局单例
_global_image_optimizer: Optional[AdvancedImageOptimizer] = None


def get_image_optimizer(reset: bool = False) -> AdvancedImageOptimizer:
    """获取或创建全局图像优化器实例"""
    global _global_image_optimizer

    if _global_image_optimizer is None or reset:
        try:
            from core.settings import get_settings
            settings = get_settings()

            # 尝试获取配置
            config = settings.get_image_optimization_config()
            compression_level = config.get('compression_level', 'aggressive')
            enable_cropping = config.get('enable_region_cropping', False)
            crop_threshold = config.get('crop_threshold', 30)

            _global_image_optimizer = AdvancedImageOptimizer(
                compression_level=compression_level,
                enable_cropping=enable_cropping,
                crop_threshold=crop_threshold
            )
            logger.info(f"高级图像优化器已初始化: 压缩={compression_level}, 裁剪={enable_cropping}")
        except Exception as e:
            logger.debug(f"从配置读取参数失败: {e}，使用默认参数")
            _global_image_optimizer = AdvancedImageOptimizer()

    return _global_image_optimizer
