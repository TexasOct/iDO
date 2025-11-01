"""
处理管道（新架构）
实现 raw_records → events/knowledge/todos → activities 的完整处理流程
"""

import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from core.models import RawRecord, RecordType
from core.logger import get_logger
from .filter_rules import EventFilter
from .summarizer_extensions import EventSummarizerExtensions
from .persistence_new import ProcessingPersistence

logger = get_logger(__name__)


class NewProcessingPipeline:
    """处理管道（新架构）"""

    def __init__(self,
                 screenshot_threshold: int = 20,
                 activity_summary_interval: int = 600,
                 knowledge_merge_interval: int = 1200,
                 todo_merge_interval: int = 1200,
                 language: str = "zh",
                 enable_screenshot_deduplication: bool = True):
        """
        初始化处理管道

        Args:
            screenshot_threshold: 多少张截图触发event提取
            activity_summary_interval: activity总结间隔（秒，默认10分钟）
            knowledge_merge_interval: knowledge合并间隔（秒，默认20分钟）
            todo_merge_interval: todo合并间隔（秒，默认20分钟）
            language: 语言设置（zh|en）
            enable_screenshot_deduplication: 是否启用截图去重
        """
        self.screenshot_threshold = screenshot_threshold
        self.activity_summary_interval = activity_summary_interval
        self.knowledge_merge_interval = knowledge_merge_interval
        self.todo_merge_interval = todo_merge_interval
        self.language = language

        # 初始化组件
        self.event_filter = EventFilter(
            enable_screenshot_deduplication=enable_screenshot_deduplication
        )
        self.summarizer = EventSummarizerExtensions(language=language)
        self.persistence = ProcessingPersistence()

        # 运行状态
        self.is_running = False

        # 截图累积器（内存中）
        self.screenshot_accumulator: List[RawRecord] = []

        # 定时任务
        self.activity_summary_task: Optional[asyncio.Task] = None
        self.knowledge_merge_task: Optional[asyncio.Task] = None
        self.todo_merge_task: Optional[asyncio.Task] = None

        # 统计信息
        self.stats = {
            "total_screenshots": 0,
            "events_created": 0,
            "knowledge_created": 0,
            "todos_created": 0,
            "activities_created": 0,
            "combined_knowledge_created": 0,
            "combined_todos_created": 0,
            "last_processing_time": None
        }

    async def start(self):
        """启动处理管道"""
        if self.is_running:
            logger.warning("处理管道已在运行中")
            return

        self.is_running = True

        # 启动定时任务
        self.activity_summary_task = asyncio.create_task(
            self._periodic_activity_summary()
        )
        self.knowledge_merge_task = asyncio.create_task(
            self._periodic_knowledge_merge()
        )
        self.todo_merge_task = asyncio.create_task(
            self._periodic_todo_merge()
        )

        logger.info(f"处理管道已启动（语言: {self.language}）")
        logger.info(f"- 截图阈值: {self.screenshot_threshold}")
        logger.info(f"- Activity总结间隔: {self.activity_summary_interval}s")
        logger.info(f"- Knowledge合并间隔: {self.knowledge_merge_interval}s")
        logger.info(f"- Todo合并间隔: {self.todo_merge_interval}s")

    async def stop(self):
        """停止处理管道"""
        if not self.is_running:
            return

        self.is_running = False

        # 取消定时任务
        if self.activity_summary_task:
            self.activity_summary_task.cancel()
        if self.knowledge_merge_task:
            self.knowledge_merge_task.cancel()
        if self.todo_merge_task:
            self.todo_merge_task.cancel()

        # 处理剩余累积的截图
        if self.screenshot_accumulator:
            logger.info(f"处理剩余的 {len(self.screenshot_accumulator)} 张截图")
            await self._extract_events(self.screenshot_accumulator)
            self.screenshot_accumulator = []

        logger.info("处理管道已停止")

    async def process_raw_records(self, raw_records: List[RawRecord]) -> Dict[str, Any]:
        """
        处理原始记录（新逻辑）

        Args:
            raw_records: 原始记录列表

        Returns:
            处理结果
        """
        if not raw_records:
            return {"processed": 0}

        try:
            logger.debug(f"接收 {len(raw_records)} 条原始记录")

            # 1. 事件过滤（包含去重）
            filtered_records = self.event_filter.filter_all_events(raw_records)
            logger.debug(f"过滤后剩余 {len(filtered_records)} 条记录")

            if not filtered_records:
                return {"processed": 0}

            # 2. 提取截图记录
            screenshots = [
                r for r in filtered_records
                if r.type == RecordType.SCREENSHOT_RECORD
            ]

            # 3. 提取键鼠记录（用于判断活跃度）
            keyboard_records = [
                r for r in filtered_records
                if r.type == RecordType.KEYBOARD_RECORD
            ]
            mouse_records = [
                r for r in filtered_records
                if r.type == RecordType.MOUSE_RECORD
            ]

            # 4. 累积截图
            self.screenshot_accumulator.extend(screenshots)
            self.stats["total_screenshots"] += len(screenshots)

            logger.debug(f"累积截图: {len(self.screenshot_accumulator)}/{self.screenshot_threshold}")

            # 5. 检查是否达到阈值
            if len(self.screenshot_accumulator) >= self.screenshot_threshold:
                # 同时传递键鼠活动信息
                await self._extract_events(
                    self.screenshot_accumulator,
                    has_keyboard_activity=len(keyboard_records) > 0,
                    has_mouse_activity=len(mouse_records) > 0
                )

                # 清空累积器
                processed_count = len(self.screenshot_accumulator)
                self.screenshot_accumulator = []

                return {
                    "processed": processed_count,
                    "accumulated": 0,
                    "extracted": True
                }

            return {
                "processed": len(screenshots),
                "accumulated": len(self.screenshot_accumulator),
                "extracted": False
            }

        except Exception as e:
            logger.error(f"处理原始记录失败: {e}", exc_info=True)
            return {"processed": 0, "error": str(e)}

    async def _extract_events(
        self,
        records: List[RawRecord],
        has_keyboard_activity: bool = False,
        has_mouse_activity: bool = False
    ):
        """
        调用LLM提取events, knowledge, todos

        Args:
            records: 记录列表（主要是截图）
            has_keyboard_activity: 是否有键盘活动
            has_mouse_activity: 是否有鼠标活动
        """
        if not records:
            return

        try:
            logger.info(f"开始提取events/knowledge/todos，共 {len(records)} 张截图")

            # 构建键鼠活动提示
            input_usage_hint = self._build_input_usage_hint(
                has_keyboard_activity,
                has_mouse_activity
            )

            # 计算事件时间戳（使用最新截图时间）
            event_timestamps = [
                record.timestamp for record in records
                if getattr(record, "timestamp", None) is not None
            ]
            event_timestamp = max(event_timestamps) if event_timestamps else datetime.now()

            # 调用summarizer提取
            result = await self.summarizer.extract_event_knowledge_todo(
                records,
                input_usage_hint=input_usage_hint
            )

            # 保存events
            events = result.get("events", [])
            for event_data in events:
                event_id = str(uuid.uuid4())
                await self.persistence.save_event({
                    "id": event_id,
                    "title": event_data["title"],
                    "description": event_data["description"],
                    "keywords": event_data.get("keywords", []),
                    "timestamp": event_timestamp
                })

            # 保存knowledge
            knowledge_list = result.get("knowledge", [])
            for knowledge_data in knowledge_list:
                knowledge_id = str(uuid.uuid4())
                await self.persistence.save_knowledge({
                    "id": knowledge_id,
                    "title": knowledge_data["title"],
                    "description": knowledge_data["description"],
                    "keywords": knowledge_data.get("keywords", []),
                    "created_at": event_timestamp
                })

            # 保存todos
            todos = result.get("todos", [])
            for todo_data in todos:
                todo_id = str(uuid.uuid4())
                await self.persistence.save_todo({
                    "id": todo_id,
                    "title": todo_data["title"],
                    "description": todo_data["description"],
                    "keywords": todo_data.get("keywords", []),
                    "created_at": event_timestamp,
                    "completed": False
                })

            # 更新统计
            self.stats["events_created"] += len(events)
            self.stats["knowledge_created"] += len(knowledge_list)
            self.stats["todos_created"] += len(todos)
            self.stats["last_processing_time"] = datetime.now()

            logger.info(
                f"提取完成: {len(events)} 个events, "
                f"{len(knowledge_list)} 个knowledge, "
                f"{len(todos)} 个todos"
            )

        except Exception as e:
            logger.error(f"提取events/knowledge/todos失败: {e}", exc_info=True)

    def _build_input_usage_hint(self, has_keyboard: bool, has_mouse: bool) -> str:
        """构建键鼠活动提示文本"""
        hints = []

        if has_keyboard:
            hints.append("用户有在使用键盘" if self.language == "zh" else "User has keyboard activity")
        else:
            hints.append("用户没有在使用键盘" if self.language == "zh" else "User has no keyboard activity")

        if has_mouse:
            hints.append("用户有在使用鼠标" if self.language == "zh" else "User has mouse activity")
        else:
            hints.append("用户没有在使用鼠标" if self.language == "zh" else "User has no mouse activity")

        return "；".join(hints) if self.language == "zh" else "; ".join(hints)

    # ============ 定时任务 ============

    async def _periodic_activity_summary(self):
        """定时任务：每N分钟总结一次activities"""
        while self.is_running:
            try:
                await asyncio.sleep(self.activity_summary_interval)
                await self._summarize_activities()
            except asyncio.CancelledError:
                logger.info("Activity总结任务已取消")
                break
            except Exception as e:
                logger.error(f"Activity总结任务异常: {e}", exc_info=True)

    async def _summarize_activities(self):
        """获取最近未总结的events，调用LLM聚合成activities"""
        try:
            # 获取未被聚合的events
            recent_events = await self.persistence.get_unsummarized_events()

            if not recent_events or len(recent_events) == 0:
                logger.debug("无待总结的events")
                return

            logger.info(f"开始聚合 {len(recent_events)} 个events 为 activities")

            # 调用summarizer聚合
            activities = await self.summarizer.aggregate_events_to_activities(
                recent_events
            )

            # 保存activities
            for activity_data in activities:
                await self.persistence.save_activity(activity_data)
                self.stats["activities_created"] += 1

            logger.info(f"成功创建 {len(activities)} 个activities")

        except Exception as e:
            logger.error(f"总结activities失败: {e}", exc_info=True)

    async def _periodic_knowledge_merge(self):
        """定时任务：每N分钟合并knowledge"""
        while self.is_running:
            try:
                await asyncio.sleep(self.knowledge_merge_interval)
                await self._merge_knowledge()
            except asyncio.CancelledError:
                logger.info("Knowledge合并任务已取消")
                break
            except Exception as e:
                logger.error(f"Knowledge合并任务异常: {e}", exc_info=True)

    async def _merge_knowledge(self):
        """合并相关的knowledge为combined_knowledge"""
        try:
            # 获取未被合并的knowledge
            unmerged_knowledge = await self.persistence.get_unmerged_knowledge()

            if not unmerged_knowledge or len(unmerged_knowledge) < 2:
                logger.debug("knowledge数量不足，跳过合并")
                return

            logger.info(f"开始合并 {len(unmerged_knowledge)} 个knowledge")

            # 调用summarizer合并
            combined = await self.summarizer.merge_knowledge(unmerged_knowledge)

            # 保存combined_knowledge
            for combined_data in combined:
                await self.persistence.save_combined_knowledge(combined_data)
                self.stats["combined_knowledge_created"] += 1

            logger.info(f"成功合并为 {len(combined)} 个combined_knowledge")

        except Exception as e:
            logger.error(f"合并knowledge失败: {e}", exc_info=True)

    async def _periodic_todo_merge(self):
        """定时任务：每N分钟合并todos"""
        while self.is_running:
            try:
                await asyncio.sleep(self.todo_merge_interval)
                await self._merge_todos()
            except asyncio.CancelledError:
                logger.info("Todo合并任务已取消")
                break
            except Exception as e:
                logger.error(f"Todo合并任务异常: {e}", exc_info=True)

    async def _merge_todos(self):
        """合并相关的todos为combined_todos"""
        try:
            # 获取未被合并的todos
            unmerged_todos = await self.persistence.get_unmerged_todos()

            if not unmerged_todos or len(unmerged_todos) < 2:
                logger.debug("todos数量不足，跳过合并")
                return

            logger.info(f"开始合并 {len(unmerged_todos)} 个todos")

            # 调用summarizer合并
            combined = await self.summarizer.merge_todos(unmerged_todos)

            # 保存combined_todos
            for combined_data in combined:
                await self.persistence.save_combined_todo(combined_data)
                self.stats["combined_todos_created"] += 1

            logger.info(f"成功合并为 {len(combined)} 个combined_todos")

        except Exception as e:
            logger.error(f"合并todos失败: {e}", exc_info=True)

    # ============ 对外接口 ============

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的events"""
        return await self.persistence.get_recent_events(limit)

    async def get_knowledge_list(self) -> List[Dict[str, Any]]:
        """获取knowledge列表（优先返回combined）"""
        return await self.persistence.get_knowledge_list()

    async def get_todo_list(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        """获取todo列表（优先返回combined）"""
        return await self.persistence.get_todo_list(include_completed)

    async def delete_knowledge(self, knowledge_id: str):
        """删除knowledge（软删除）"""
        await self.persistence.delete_knowledge(knowledge_id)

    async def delete_todo(self, todo_id: str):
        """删除todo（软删除）"""
        await self.persistence.delete_todo(todo_id)

    async def generate_diary_for_date(self, date: str) -> Dict[str, Any]:
        """为指定日期生成日记"""
        try:
            # 检查是否已存在
            existing = await self.persistence.get_diary_by_date(date)
            if existing:
                return existing

            # 获取该日期的所有activities
            activities = await self.persistence.get_activities_by_date(date)

            if not activities:
                return {
                    "error": "该日期无活动记录" if self.language == "zh" else "No activities for this date"
                }

            # 调用summarizer生成日记
            diary_content = await self.summarizer.generate_diary(activities, date)

            # 保存日记
            diary_id = str(uuid.uuid4())
            diary_data = {
                "id": diary_id,
                "date": date,
                "content": diary_content,
                "source_activity_ids": [a["id"] for a in activities],
                "created_at": datetime.now()
            }

            await self.persistence.save_diary(diary_data)
            return diary_data

        except Exception as e:
            logger.error(f"生成日记失败: {e}", exc_info=True)
            return {"error": str(e)}

    async def delete_diary(self, diary_id: str):
        """删除日记"""
        await self.persistence.delete_diary(diary_id)

    async def get_diary_list(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的日记列表"""
        return await self.persistence.get_diary_list(limit)

    async def force_finalize_activity(self):
        """手动触发一次活动总结和知识/待办合并"""
        try:
            await self._summarize_activities()
            await self._merge_knowledge()
            await self._merge_todos()
        except Exception as exc:
            logger.error(f"强制完成活动失败: {exc}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "is_running": self.is_running,
            "screenshot_threshold": self.screenshot_threshold,
            "accumulated_screenshots": len(self.screenshot_accumulator),
            "stats": self.stats.copy()
        }
