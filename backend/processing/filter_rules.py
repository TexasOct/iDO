"""
事件筛选规则
实现键盘、鼠标事件的智能筛选逻辑
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from core.models import RawRecord, RecordType
from core.logger import get_logger

logger = get_logger(__name__)


class EventFilter:
    """事件筛选器"""
    
    def __init__(self):
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
        last_screenshot_time = None
        screenshot_interval = 1.0  # 1秒内的重复截图会被过滤
        
        for record in records:
            if record.type != RecordType.SCREENSHOT_RECORD:
                continue
            
            # 检查时间间隔
            if (last_screenshot_time is None or 
                (record.timestamp - last_screenshot_time).total_seconds() >= screenshot_interval):
                filtered_records.append(record)
                last_screenshot_time = record.timestamp
                logger.debug(f"保留屏幕截图: {record.timestamp}")
            else:
                logger.debug(f"过滤重复屏幕截图: {record.timestamp}")
        
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
            data=self._merge_event_data(group)
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
        first_data = group[0].data
        last_data = group[-1].data
        
        return {
            "action": "sequence",
            "width": first_data.get("width", 0),
            "height": first_data.get("height", 0),
            "format": first_data.get("format", "unknown"),
            "count": len(group),
            "duration": (group[-1].timestamp - group[0].timestamp).total_seconds(),
            "start_time": group[0].timestamp.isoformat(),
            "end_time": group[-1].timestamp.isoformat(),
            "merged": True
        }
    
    def filter_all_events(self, records: List[RawRecord]) -> List[RawRecord]:
        """筛选所有事件"""
        logger.info(f"开始筛选事件，原始记录数: {len(records)}")
        
        # 按类型筛选
        keyboard_events = self.filter_keyboard_events(records)
        mouse_events = self.filter_mouse_events(records)
        screenshot_events = self.filter_screenshot_events(records)
        
        # 合并所有筛选后的事件
        all_filtered = keyboard_events + mouse_events + screenshot_events
        
        # 按时间排序
        all_filtered.sort(key=lambda x: x.timestamp)
        
        # 合并连续事件
        merged_events = self.merge_consecutive_events(all_filtered)
        
        logger.info(f"筛选完成，最终记录数: {len(merged_events)}")
        logger.info(f"键盘事件: {len(keyboard_events)}, 鼠标事件: {len(mouse_events)}, 屏幕截图: {len(screenshot_events)}")
        
        return merged_events
