"""
用户活跃度检测器
检测键盘和鼠标输入活动，判断用户是否在活跃使用电脑
"""

from typing import List
from datetime import datetime, timedelta
from core.models import RawRecord
from core.logger import get_logger

logger = get_logger(__name__)


class ActivityDetector:
    """用户活跃度检测器"""

    def __init__(self, activity_threshold_seconds: int = 30):
        """
        初始化活跃度检测器

        Args:
            activity_threshold_seconds: 活跃判断阈值（秒），在此时间内有键鼠输入则认为活跃
        """
        self.activity_threshold = activity_threshold_seconds

    def has_user_activity(self, records: List[RawRecord]) -> bool:
        """
        检测记录中是否包含用户活跃行为（键盘或鼠标输入）

        Args:
            records: 原始记录列表

        Returns:
            True 表示有活跃行为，False 表示无活跃行为
        """
        if not records:
            return False

        # 统计键盘和鼠标输入事件
        keyboard_count = 0
        mouse_click_count = 0
        mouse_move_count = 0

        for record in records:
            if record.type == "keyboard":
                keyboard_count += 1
            elif record.type == "mouse":
                action = record.data.get("action", "")
                if action in ["click", "double_click", "right_click", "middle_click"]:
                    mouse_click_count += 1
                elif action == "move":
                    mouse_move_count += 1

        # 判断逻辑：有任何键盘输入或鼠标点击即认为活跃
        has_activity = keyboard_count > 0 or mouse_click_count > 0

        if has_activity:
            logger.debug(
                f"检测到用户活跃: "
                f"键盘={keyboard_count}, "
                f"鼠标点击={mouse_click_count}, "
                f"鼠标移动={mouse_move_count}"
            )
        else:
            logger.debug(
                f"未检测到用户活跃输入: "
                f"键盘={keyboard_count}, "
                f"鼠标点击={mouse_click_count}, "
                f"鼠标移动={mouse_move_count} (仅截图)"
            )

        return has_activity

    def filter_inactive_periods(self, records: List[RawRecord]) -> List[RawRecord]:
        """
        过滤掉非活跃期间的记录

        将记录按时间窗口分组，只保留有键鼠活动的窗口内的记录

        Args:
            records: 原始记录列表

        Returns:
            过滤后的记录列表
        """
        if not records:
            return []

        # 按时间排序
        sorted_records = sorted(records, key=lambda x: x.timestamp)

        # 找出所有有键鼠输入的时间点
        active_timestamps = []
        for record in sorted_records:
            if record.type in ["keyboard", "mouse"]:
                action = record.data.get("action", "") if record.type == "mouse" else "key"
                # 只记录实际输入行为（键盘按键、鼠标点击）
                if record.type == "keyboard" or action in ["click", "double_click", "right_click", "middle_click"]:
                    active_timestamps.append(record.timestamp)

        if not active_timestamps:
            logger.debug("记录中无键鼠输入活动，过滤所有记录")
            return []

        # 过滤记录：只保留活跃时间点附近的记录
        filtered = []
        for record in sorted_records:
            # 检查是否在任何活跃时间点的阈值范围内
            is_near_activity = any(
                abs((record.timestamp - active_time).total_seconds()) <= self.activity_threshold
                for active_time in active_timestamps
            )

            if is_near_activity:
                filtered.append(record)

        if len(filtered) < len(sorted_records):
            logger.debug(f"过滤非活跃记录: {len(sorted_records)} → {len(filtered)}")

        return filtered

    def get_activity_periods(self, records: List[RawRecord]) -> List[tuple]:
        """
        获取活跃时间段列表

        Args:
            records: 原始记录列表

        Returns:
            活跃时间段列表 [(start_time, end_time), ...]
        """
        if not records:
            return []

        # 找出所有键鼠输入时间点
        active_timestamps = []
        for record in records:
            if record.type in ["keyboard", "mouse"]:
                action = record.data.get("action", "") if record.type == "mouse" else "key"
                if record.type == "keyboard" or action in ["click", "double_click", "right_click", "middle_click"]:
                    active_timestamps.append(record.timestamp)

        if not active_timestamps:
            return []

        # 按时间排序
        active_timestamps.sort()

        # 合并相近的时间点为时间段
        periods = []
        current_start = active_timestamps[0]
        current_end = active_timestamps[0]

        for timestamp in active_timestamps[1:]:
            if (timestamp - current_end).total_seconds() <= self.activity_threshold:
                # 扩展当前时间段
                current_end = timestamp
            else:
                # 结束当前时间段，开始新时间段
                periods.append((
                    current_start - timedelta(seconds=self.activity_threshold),
                    current_end + timedelta(seconds=self.activity_threshold)
                ))
                current_start = timestamp
                current_end = timestamp

        # 添加最后一个时间段
        periods.append((
            current_start - timedelta(seconds=self.activity_threshold),
            current_end + timedelta(seconds=self.activity_threshold)
        ))

        return periods
