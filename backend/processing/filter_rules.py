"""
事件筛选规则
实现键盘、鼠标事件的智能筛选逻辑
添加截图去重功能
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from core.models import RawRecord, RecordType
from core.logger import get_logger
import base64
import io
from processing.image_manager import get_image_manager

logger = get_logger(__name__)

# 尝试导入imagehash和PIL
try:
    import imagehash
    from PIL import Image
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logger.warning("imagehash或PIL库未安装，截图去重功能将被禁用")


class EventFilter:
    """事件筛选器 - 支持截图去重"""

    def __init__(self, enable_screenshot_deduplication: bool = True, hash_threshold: int = 5):
        """
        初始化事件筛选器

        Args:
            enable_screenshot_deduplication: 是否启用截图去重
            hash_threshold: 感知哈希差异阈值，小于此值认为图片相同
        """
        self.keyboard_special_keys = {
            'enter', 'space', 'tab', 'backspace', 'delete',
            'up', 'down', 'left', 'right',
            'home', 'end', 'page_up', 'page_down',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            'esc', 'caps_lock', 'num_lock', 'scroll_lock',
            'insert', 'print_screen', 'pause'
        }

        self.mouse_important_actions = {
            'press', 'release', 'drag', 'drag_end', 'scroll'
        }

        self.scroll_merge_threshold = 0.1  # 100ms 内的滚动事件会被合并
        self.click_merge_threshold = 0.5   # 500ms 内的点击事件会被合并
        self.min_screenshots_per_window = 2

        # 截图去重配置
        self.enable_screenshot_deduplication = enable_screenshot_deduplication and IMAGEHASH_AVAILABLE
        self.hash_threshold = hash_threshold
        self.last_screenshot_hash = None
        self.image_manager = get_image_manager()

        if enable_screenshot_deduplication and not IMAGEHASH_AVAILABLE:
            logger.warning("截图去重功能已禁用（缺少依赖库）")

    def filter_duplicate_screenshots(self, records: List[RawRecord]) -> List[RawRecord]:
        """
        去除连续重复的截图
        使用感知哈希（perceptual hash）判断图片是否一模一样

        Args:
            records: 原始记录列表

        Returns:
            过滤后的记录列表
        """
        if not self.enable_screenshot_deduplication:
            return records

        filtered = []

        for record in records:
            # 非截图记录直接保留
            if record.type != RecordType.SCREENSHOT_RECORD:
                filtered.append(record)
                continue

            # 计算截图的感知哈希
            try:
                img_hash = self._compute_image_hash(record)

                if img_hash is None:
                    # 无法计算哈希，保留记录
                    filtered.append(record)
                    continue

                # 检查是否与上一张截图重复
                if self.last_screenshot_hash is not None:
                    hash_diff = img_hash - self.last_screenshot_hash

                    if hash_diff <= self.hash_threshold:
                        # 图片重复，跳过
                        logger.debug(f"跳过重复截图，哈希差异: {hash_diff}")
                        continue

                # 不重复，保留并更新last_hash
                self.last_screenshot_hash = img_hash
                filtered.append(record)

            except Exception as e:
                logger.warning(f"处理截图哈希失败: {e}，保留该截图")
                filtered.append(record)

        if len(filtered) < len(records):
            logger.debug(f"截图去重: {len(records)} → {len(filtered)} 条记录")

        return filtered

    def _compute_image_hash(self, record: RawRecord) -> Optional[Any]:
        """
        计算截图的感知哈希

        Args:
            record: 截图记录

        Returns:
            imagehash对象，或None
        """
        if not IMAGEHASH_AVAILABLE:
            return None

        try:
            data = record.data or {}

            # 尝试从data中获取base64图片数据
            img_data_b64 = data.get("img_data")
            if not img_data_b64:
                return None

            # 解码base64
            img_bytes = base64.b64decode(img_data_b64)
            img = Image.open(io.BytesIO(img_bytes))

            # 计算感知哈希
            phash = imagehash.phash(img)
            return phash

        except Exception as e:
            logger.debug(f"计算图片哈希失败: {e}")
            # 尝试通过 hash 从内存缓存或缩略图加载图片
            try:
                img_hash = (record.data or {}).get("hash")
                if not img_hash:
                    return None

                # 先从内存缓存获取
                cached_data = self.image_manager.get_from_memory_cache(img_hash)
                if cached_data:
                    img_bytes = base64.b64decode(cached_data)
                    img = Image.open(io.BytesIO(img_bytes))
                    return imagehash.phash(img)

                # 回退到磁盘缩略图
                thumbnail_data = self.image_manager.load_thumbnail_base64(img_hash)
                if thumbnail_data:
                    img_bytes = base64.b64decode(thumbnail_data)
                    img = Image.open(io.BytesIO(img_bytes))
                    return imagehash.phash(img)

            except Exception as exc:
                logger.debug(f"根据hash加载图片失败: {exc}")
                return None

            return None

    def reset_deduplication_state(self):
        """重置去重状态"""
        self.last_screenshot_hash = None
    
    def filter_keyboard_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """筛选键盘事件，目前保留所有键盘记录"""
        filtered_records = [
            record for record in records
            if record.type == RecordType.KEYBOARD_RECORD
        ]

        for record in filtered_records:
            logger.debug(f"保留键盘事件: {record.data.get('key', 'unknown')}")

        return filtered_records
    
    def filter_mouse_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """筛选鼠标事件"""
        filtered_records = []
        
        for record in records:
            if record.type != RecordType.MOUSE_RECORD:
                continue
            
            # 检查是否为重要鼠标事件
            if self._is_important_mouse_event(record):
                filtered_records.append(record)
                logger.debug(f"保留鼠标事件: {record.data.get('action', 'unknown')}")
            else:
                logger.debug(f"过滤鼠标事件: {record.data.get('action', 'unknown')}")
        
        return filtered_records
    
    def filter_screenshot_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """筛选屏幕截图事件"""
        filtered_records = []
        last_window_start = None
        screenshots_in_window = 0
        screenshot_interval = 1.0  # 滑动窗口长度（秒）
        
        for record in records:
            if record.type != RecordType.SCREENSHOT_RECORD:
                continue

            if last_window_start is None:
                last_window_start = record.timestamp
                screenshots_in_window = 0

            elapsed = (record.timestamp - last_window_start).total_seconds()

            # 超出窗口时重置计数
            if elapsed >= screenshot_interval:
                last_window_start = record.timestamp
                screenshots_in_window = 0

            if elapsed < screenshot_interval and screenshots_in_window >= self.min_screenshots_per_window:
                logger.debug(f"过滤重复屏幕截图: {record.timestamp}")
                continue

            filtered_records.append(record)
            screenshots_in_window += 1
            logger.debug(f"保留屏幕截图: {record.timestamp}")
        
        return filtered_records
    
    def merge_consecutive_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """合并连续事件"""
        if not records:
            return []
        
        merged_records = []
        current_group = [records[0]]
        
        for i in range(1, len(records)):
            current_record = records[i]
            previous_record = records[i-1]
            
            # 检查是否可以合并
            if self._can_merge_events(previous_record, current_record):
                current_group.append(current_record)
            else:
                # 合并当前组
                merged_record = self._merge_event_group(current_group)
                if merged_record:
                    merged_records.append(merged_record)
                
                # 开始新组
                current_group = [current_record]
        
        # 处理最后一组
        if current_group:
            merged_record = self._merge_event_group(current_group)
            if merged_record:
                merged_records.append(merged_record)
        
        return merged_records
    
    def _is_special_keyboard_event(self, record: RawRecord) -> bool:
        """判断是否为特殊键盘事件"""
        data = record.data
        key = data.get("key", "").lower()
        action = data.get("action", "")
        modifiers = data.get("modifiers", [])
        
        # 特殊键
        if key in self.keyboard_special_keys:
            return True
        
        # 带修饰键的普通键
        if modifiers and len(modifiers) > 0:
            return True
        
        # 特殊动作
        if action in ["press", "release"] and key in ["ctrl", "alt", "shift", "cmd"]:
            return True
        
        return False
    
    def _is_important_mouse_event(self, record: RawRecord) -> bool:
        """判断是否为重要鼠标事件"""
        data = record.data
        action = data.get("action", "")
        
        return action in self.mouse_important_actions
    
    def _can_merge_events(self, prev_record: RawRecord, curr_record: RawRecord) -> bool:
        """判断两个事件是否可以合并"""
        # 不同类型的事件不能合并
        if prev_record.type != curr_record.type:
            return False
        
        # 时间间隔检查
        time_diff = (curr_record.timestamp - prev_record.timestamp).total_seconds()
        
        if prev_record.type == RecordType.KEYBOARD_RECORD:
            # 键盘事件：100ms 内的相同键可以合并
            return (time_diff <= 0.1 and 
                    prev_record.data.get("key") == curr_record.data.get("key"))
        
        elif prev_record.type == RecordType.MOUSE_RECORD:
            # 鼠标事件：根据动作类型判断
            prev_action = prev_record.data.get("action", "")
            curr_action = curr_record.data.get("action", "")
            
            if prev_action == "scroll" and curr_action == "scroll":
                return time_diff <= self.scroll_merge_threshold
            
            if prev_action == "press" and curr_action == "release":
                return time_diff <= self.click_merge_threshold
            
            return False
        
        elif prev_record.type == RecordType.SCREENSHOT_RECORD:
            # 屏幕截图：1秒内的可以合并
            return time_diff <= 1.0
        
        return False
    
    def _merge_event_group(self, group: List[RawRecord]) -> RawRecord:
        """合并事件组"""
        if not group:
            return None
        
        if len(group) == 1:
            return group[0]
        
        # 创建合并后的事件
        merged_record = RawRecord(
            timestamp=group[0].timestamp,
            type=group[0].type,
            data=self._merge_event_data(group),
            screenshot_path=getattr(group[0], "screenshot_path", None)
        )
        
        # 添加源事件信息
        merged_record.source_events = group
        
        return merged_record
    
    def _merge_event_data(self, group: List[RawRecord]) -> Dict[str, Any]:
        """合并事件数据"""
        if not group:
            return {}
        
        first_record = group[0]
        event_type = first_record.type
        
        if event_type == RecordType.KEYBOARD_RECORD:
            return self._merge_keyboard_data(group)
        elif event_type == RecordType.MOUSE_RECORD:
            return self._merge_mouse_data(group)
        elif event_type == RecordType.SCREENSHOT_RECORD:
            return self._merge_screenshot_data(group)
        else:
            return first_record.data
    
    def _merge_keyboard_data(self, group: List[RawRecord]) -> Dict[str, Any]:
        """合并键盘事件数据"""
        first_data = group[0].data
        last_data = group[-1].data
        
        return {
            "action": "sequence",
            "key": first_data.get("key", "unknown"),
            "key_type": first_data.get("key_type", "unknown"),
            "modifiers": first_data.get("modifiers", []),
            "count": len(group),
            "duration": (group[-1].timestamp - group[0].timestamp).total_seconds(),
            "start_time": group[0].timestamp.isoformat(),
            "end_time": group[-1].timestamp.isoformat(),
            "merged": True
        }
    
    def _merge_mouse_data(self, group: List[RawRecord]) -> Dict[str, Any]:
        """合并鼠标事件数据"""
        first_data = group[0].data
        last_data = group[-1].data
        
        if first_data.get("action") == "scroll":
            # 合并滚动事件
            total_dx = sum(record.data.get("dx", 0) for record in group)
            total_dy = sum(record.data.get("dy", 0) for record in group)
            
            return {
                "action": "scroll",
                "position": last_data.get("position", (0, 0)),
                "dx": total_dx,
                "dy": total_dy,
                "count": len(group),
                "duration": (group[-1].timestamp - group[0].timestamp).total_seconds(),
                "start_time": group[0].timestamp.isoformat(),
                "end_time": group[-1].timestamp.isoformat(),
                "merged": True
            }
        
        elif first_data.get("action") == "press" and last_data.get("action") == "release":
            # 合并点击事件
            return {
                "action": "click",
                "button": first_data.get("button", "unknown"),
                "start_position": first_data.get("position", (0, 0)),
                "end_position": last_data.get("position", (0, 0)),
                "duration": (group[-1].timestamp - group[0].timestamp).total_seconds(),
                "start_time": group[0].timestamp.isoformat(),
                "end_time": group[-1].timestamp.isoformat(),
                "merged": True
            }
        
        else:
            # 其他情况，返回第一个事件的数据
            return first_data
    
    def _merge_screenshot_data(self, group: List[RawRecord]) -> Dict[str, Any]:
        """合并屏幕截图数据"""
        first_data = (group[0].data or {}).copy()
        last_data = group[-1].data or {}

        sequence_meta = {
            "sequenceCount": len(group),
            "sequenceDuration": (group[-1].timestamp - group[0].timestamp).total_seconds(),
            "sequenceStart": group[0].timestamp.isoformat(),
            "sequenceEnd": group[-1].timestamp.isoformat()
        }

        # 保留原始截图信息，同时补充序列元数据
        merged_data = {
            **first_data,
            "merged": True,
            "sequenceMeta": sequence_meta
        }

        # 如果存在后续截图的哈希或路径，保留最新值用于缓存匹配
        for field in ("hash", "screenshotPath", "img_data"):
            if field not in merged_data and field in last_data:
                merged_data[field] = last_data[field]

        if "screenshotPath" not in merged_data and getattr(group[0], "screenshot_path", None):
            merged_data["screenshotPath"] = group[0].screenshot_path

        return merged_data
    
    def filter_all_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """筛选所有事件（包含截图去重）"""
        logger.info(f"开始筛选事件，原始记录数: {len(records)}")

        # 第一步：截图去重
        dedup_records = self.filter_duplicate_screenshots(records)

        # 按类型筛选
        keyboard_events = self.filter_keyboard_events(dedup_records)
        mouse_events = self.filter_mouse_events(dedup_records)
        screenshot_events = self.filter_screenshot_events(dedup_records)

        # 合并所有筛选后的事件
        all_filtered = keyboard_events + mouse_events + screenshot_events

        # 按时间排序
        all_filtered.sort(key=lambda x: x.timestamp)

        # 合并连续事件
        merged_events = self.merge_consecutive_events(all_filtered)

        logger.info(f"筛选完成，最终记录数: {len(merged_events)}")
        logger.info(f"键盘事件: {len(keyboard_events)}, 鼠标事件: {len(mouse_events)}, 屏幕截图: {len(screenshot_events)}")

        return merged_events
