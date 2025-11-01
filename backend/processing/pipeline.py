"""
处理管道
实现 raw_records → events → activity 的完整处理流程
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.models import RawRecord, Event, RecordType
from core.logger import get_logger
from .filter_rules import EventFilter
from .summarizer import EventSummarizer
from .merger import ActivityMerger
from .persistence import ProcessingPersistence
from .activity_detector import ActivityDetector

logger = get_logger(__name__)


class ProcessingPipeline:
    """处理管道"""

    def __init__(self,
                 processing_interval: int = 30,
                 persistence: Optional[ProcessingPersistence] = None,
                 activity_threshold: int = 30):
        """
        初始化处理管道

        Args:
            processing_interval: 处理间隔（秒）
            persistence: 持久化处理器
            activity_threshold: 用户活跃判断阈值（秒）
        """
        self.processing_interval = processing_interval
        self.persistence = persistence or ProcessingPersistence()

        # 初始化处理器
        self.event_filter = EventFilter()
        self.summarizer = EventSummarizer()
        self.merger = ActivityMerger()
        self.activity_detector = ActivityDetector(activity_threshold)
        self.min_screenshots_per_event = 2

        # 运行状态
        self.is_running = False
        self.current_activity = None
        self.last_processing_time = None

        # 统计信息
        self.stats = {
            "total_processed": 0,
            "events_created": 0,
            "activities_created": 0,
            "activities_merged": 0,
            "last_processing_time": None
        }

    async def start(self):
        """启动处理管道"""
        if self.is_running:
            logger.warning("处理管道已在运行中")
            return

        self.is_running = True
        logger.info(f"处理管道已启动，处理间隔: {self.processing_interval} 秒")

    async def stop(self):
        """停止处理管道"""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("处理管道已停止")

    async def process_raw_records(self, raw_records: List[RawRecord]) -> Dict[str, Any]:
        """处理原始记录"""
        if not raw_records:
            return {"events": [], "activities": [], "merged": False}

        try:
            logger.info(f"开始处理 {len(raw_records)} 条原始记录")

            # 1. 事件筛选
            filtered_records = self.event_filter.filter_all_events(raw_records)
            logger.debug(f"筛选后剩余 {len(filtered_records)} 条记录")

            if not filtered_records:
                logger.info("筛选后无有效记录")
                return {"events": [], "activities": [], "merged": False}

            # 2. 创建事件
            events = await self._create_events(filtered_records)
            logger.debug(f"创建了 {len(events)} 个事件")

            # 3. 处理活动
            activity_result = await self._process_activities(events)

            # 4. 更新统计
            self._update_stats(len(raw_records), len(events), activity_result)

            # 准确显示统计信息
            completed_count = len(activity_result.get('activities', []))  # 已持久化的活动数
            current_activity_id = activity_result.get('current_activity_id')

            if completed_count > 0:
                if current_activity_id:
                    logger.info(f"处理完成: {len(events)} 个事件 → {completed_count} 个活动已持久化, 1 个活动正在进行中 ({current_activity_id[:8]}...)")
                else:
                    logger.info(f"处理完成: {len(events)} 个事件 → {completed_count} 个活动已持久化")
            else:
                if current_activity_id:
                    logger.info(f"处理完成: {len(events)} 个事件 → 合并到正在进行的活动 ({current_activity_id[:8]}...)")
                else:
                    logger.info(f"处理完成: {len(events)} 个事件 → 无活动变化")

            return {
                "events": events,
                "activities": activity_result.get("activities", []),
                "merged": activity_result.get("merged", False),
                "current_activity_id": current_activity_id
            }

        except Exception as e:
            logger.error(f"处理原始记录失败: {e}")
            return {"events": [], "activities": [], "merged": False}

    async def _create_events(self, filtered_records: List[RawRecord]) -> List[Event]:
        """创建事件"""
        events = []

        # 按时间分组记录（每10秒一组）
        grouped_records = self._group_records_by_time(
            filtered_records,
            10,
            self.min_screenshots_per_event
        )

        for group in grouped_records:
            if not group:
                continue

            # 为每组记录创建一个事件
            event = await self._create_single_event(group)
            if event:
                events.append(event)

        return events

    def _group_records_by_time(
        self,
        records: List[RawRecord],
        interval_seconds: int,
        min_screenshots: int
    ) -> List[List[RawRecord]]:
        """按时间间隔分组记录，并确保每组至少包含指定数量的截图"""
        if not records:
            return []

        # 按时间排序
        sorted_records = sorted(records, key=lambda x: x.timestamp)

        groups: List[List[RawRecord]] = []
        index = 0
        total = len(sorted_records)

        while index < total:
            group: List[RawRecord] = []
            start_time = sorted_records[index].timestamp
            screenshot_count = 0

            # 先按时间窗口收集记录，若截图不足将继续扩展
            while index < total:
                record = sorted_records[index]
                time_diff = (record.timestamp - start_time).total_seconds()

                if group and time_diff > interval_seconds and screenshot_count >= min_screenshots:
                    break

                group.append(record)
                if record.type == RecordType.SCREENSHOT_RECORD:
                    screenshot_count += 1

                index += 1

                if time_diff > interval_seconds and screenshot_count >= min_screenshots:
                    break

            # 若截图不足，继续吸收后续记录直到满足要求或无记录
            while screenshot_count < min_screenshots and index < total:
                record = sorted_records[index]
                group.append(record)
                if record.type == RecordType.SCREENSHOT_RECORD:
                    screenshot_count += 1
                index += 1

            if screenshot_count >= min_screenshots:
                groups.append(group)
            else:
                logger.warning(
                    "跳过截图不足的记录组: %d 条记录，仅 %d 张截图",
                    len(group),
                    screenshot_count
                )

        return groups

    async def _create_single_event(self, records: List[RawRecord]) -> Optional[Event]:
        """创建单个事件"""
        if not records:
            return None

        try:
            screenshot_count = sum(
                1 for record in records if record.type == RecordType.SCREENSHOT_RECORD
            )
            if screenshot_count < self.min_screenshots_per_event:
                logger.warning(
                    "跳过截图不足的事件组: %d 张截图，期望至少 %d 张",
                    screenshot_count,
                    self.min_screenshots_per_event
                )
                return None

            # 检查是否有用户活跃行为（键鼠输入）
            # if not self.activity_detector.has_user_activity(records):
            #     logger.debug("记录中无键鼠输入活动，跳过事件创建")
            #     return None

            # 计算时间范围
            start_time = min(record.timestamp for record in records)
            end_time = max(record.timestamp for record in records)

            # 生成事件摘要
            summary = await self.summarizer.summarize_events(records)

            # 过滤掉无有效内容的事件
            if summary == "无有效内容":
                logger.debug("跳过无有效内容的事件")
                return None

            # 创建事件
            event = Event(
                id=str(uuid.uuid4()),
                start_time=start_time,
                end_time=end_time,
                summary=summary,
                source_data=records
            )

            # 持久化事件
            await self.persistence.save_event(event)

            return event

        except Exception as e:
            logger.error(f"创建事件失败: {e}")
            return None

    async def _process_activities(self, events: List[Event]) -> Dict[str, Any]:
        """处理活动 - 顺序遍历events，逐个判断是否合并"""
        if not events:
            return {"activities": [], "merged": False, "new_activities_count": 0}

        # 过滤掉summary为"无有效内容"的事件
        valid_events = [event for event in events if event.summary != "无有效内容"]
        if not valid_events:
            logger.info("所有事件均为无有效内容，跳过活动处理")
            return {"activities": [], "merged": False, "new_activities_count": 0}

        activities = []
        merged = False
        new_activities_count = 0  # 本次新创建的活动数量

        # 顺序遍历所有events
        for event in valid_events:
            if not self.current_activity:
                # 没有当前活动，创建第一个活动
                self.current_activity = await self._create_activity_from_event(event)
                new_activities_count += 1
                logger.info(f"创建第一个活动: {self.current_activity['id']}")
            else:
                # 有当前活动，判断是否合并
                should_merge, merged_title, merged_description = await self.merger._llm_judge_merge(
                    self.current_activity, event
                )

                if should_merge:
                    # 合并到当前活动
                    self.current_activity = await self.merger.merge_activity_with_event(
                        self.current_activity, event, merged_title, merged_description
                    )
                    merged = True
                    logger.info("事件已合并到当前活动")
                else:
                    # 不合并，保存当前活动并创建新活动
                    # 确保不保存无有效内容的活动
                    if self.current_activity.get('description') != "无有效内容":
                        await self.persistence.save_activity(self.current_activity)
                        activities.append(self.current_activity)
                        logger.info(f"保存活动: {self.current_activity['id']}")
                    else:
                        logger.warning(f"跳过保存无有效内容的活动: {self.current_activity['id']}")

                    # 创建新活动
                    self.current_activity = await self._create_activity_from_event(event)
                    new_activities_count += 1  # 只在创建时计数
                    logger.info(f"创建新活动: {self.current_activity['id']}")

        # 注意：self.current_activity 保持不变，不加入返回列表
        # 只有当不能合并或强制停止时才会持久化

        return {
            "activities": activities,  # 只包含已持久化的活动
            "merged": merged,
            "new_activities_count": new_activities_count,
            "current_activity_id": self.current_activity['id'] if self.current_activity else None
        }

    async def _create_activity_from_event(self, event: Event) -> Dict[str, Any]:
        """从单个事件创建活动"""
        try:
            # 额外的安全检查：确保不会基于无效事件创建活动
            if event.summary == "无有效内容":
                logger.warning("尝试从无有效内容的事件创建活动，这不应该发生")
                raise ValueError("不能从无有效内容的事件创建活动")

            # 通过LLM生成初始活动标题和描述
            metadata = await self.summarizer.generate_activity_metadata(event.summary)
            title = metadata.get("title", event.summary)
            description = metadata.get("description", event.summary)

            activity = {
                "id": str(uuid.uuid4()),
                "title": title,  # 活动标题
                "description": description,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "source_events": [event],  # 将event添加到source_events
                "event_count": 1,
                "created_at": datetime.now()
            }

            logger.info(f"从事件创建活动: {activity['id']} - {title}")
            return activity

        except Exception as e:
            logger.error(f"从事件创建活动失败: {e}")
            raise

    async def _create_new_activity(self, events: List[Event]) -> Optional[Dict[str, Any]]:
        """创建新活动"""
        if not events:
            return None

        try:
            # 计算时间范围
            all_records = []
            for event in events:
                all_records.extend(event.source_data)

            start_time = min(record.timestamp for record in all_records)
            end_time = max(record.timestamp for record in all_records)

            # 生成活动描述
            description = await self.summarizer.summarize_activity(all_records)

            # 创建活动
            activity = {
                "id": str(uuid.uuid4()),
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "source_events": events,
                "event_count": len(all_records),
                "created_at": datetime.now()
            }

            logger.info(f"创建新活动: {activity['id']} - {description}")
            return activity

        except Exception as e:
            logger.error(f"创建新活动失败: {e}")
            return None

    def _update_stats(self, raw_count: int, event_count: int, activity_result: Dict[str, Any]):
        """更新统计信息"""
        self.stats["total_processed"] += raw_count
        self.stats["events_created"] += event_count
        self.stats["last_processing_time"] = datetime.now()

        activities = activity_result.get("activities", [])
        if activity_result.get("merged", False):
            self.stats["activities_merged"] += 1
        else:
            self.stats["activities_created"] += len(activities)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "is_running": self.is_running,
            "processing_interval": self.processing_interval,
            "current_activity": self.current_activity is not None,
            "stats": self.stats.copy()
        }

    def set_processing_interval(self, interval: int):
        """设置处理间隔"""
        self.processing_interval = max(1, interval)
        logger.info(f"处理间隔设置为: {self.processing_interval} 秒")

    async def force_finalize_activity(self):
        """强制完成当前活动"""
        if self.current_activity:
            try:
                # 检查活动描述是否有效
                if self.current_activity.get('description') == "无有效内容":
                    logger.info(f"跳过保存无有效内容的活动: {self.current_activity['id']}")
                    self.current_activity = None
                    return

                await self.persistence.save_activity(self.current_activity)
                logger.info(f"强制完成活动: {self.current_activity['id']}")
                self.current_activity = None
            except Exception as e:
                logger.error(f"强制完成活动失败: {e}")

    async def get_recent_activities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的活动"""
        try:
            return await self.persistence.get_recent_activities(limit)
        except Exception as e:
            logger.error(f"获取最近活动失败: {e}")
            return []

    async def get_recent_events(self, limit: int = 50) -> List[Event]:
        """获取最近的事件"""
        try:
            return await self.persistence.get_recent_events(limit)
        except Exception as e:
            logger.error(f"获取最近事件失败: {e}")
            return []
