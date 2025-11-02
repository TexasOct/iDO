"""
EventSummarizer（新架构）
统一处理事件提取、合并、日记生成等 LLM 交互能力
"""

import uuid
import json
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.models import RawRecord, RecordType
from core.json_parser import parse_json_from_response
from core.logger import get_logger
from llm.client import get_llm_client
from llm.prompt_manager import get_prompt_manager
from processing.image_manager import get_image_manager
from processing.image_compression import get_image_optimizer

logger = get_logger(__name__)


class EventSummarizer:
    """事件处理/总结入口（新架构）"""

    def __init__(self, llm_client=None, language: str = "zh"):
        """
        Args:
            llm_client: LLM客户端实例
            language: 语言设置 (zh | en)
        """
        self.llm_client = llm_client or get_llm_client()
        self.prompt_manager = get_prompt_manager(language)
        self.language = language
        self.image_manager = get_image_manager()
        self.image_optimizer = None

        try:
            self.image_optimizer = get_image_optimizer()
            logger.info("EventSummarizer: 图像优化已启用")
        except Exception as exc:
            logger.warning(f"EventSummarizer: 初始化图像优化失败，将跳过压缩: {exc}")
            self.image_optimizer = None
        # 简单的结果缓存，可按需复用
        self._summary_cache: Dict[str, str] = {}

    # ============ Event/Knowledge/Todo提取 ============

    async def extract_event_knowledge_todo(
        self,
        records: List[RawRecord],
        input_usage_hint: str = ""
    ) -> Dict[str, Any]:
        """
        从raw_records提取events, knowledge, todos

        Args:
            records: 原始记录列表（主要是截图）
            input_usage_hint: 键鼠活动提示

        Returns:
            {
                "events": [...],
                "knowledge": [...],
                "todos": [...]
            }
        """
        if not records:
            return {"events": [], "knowledge": [], "todos": []}

        try:
            logger.info(f"开始提取事件/知识/待办，共 {len(records)} 条记录")

            # 构建消息（包含截图）
            messages = await self._build_extraction_messages(records, input_usage_hint)

            # 获取配置参数
            config_params = self.prompt_manager.get_config_params("event_extraction")

            # 调用LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # 解析JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"LLM返回格式错误: {content[:200]}")
                return {"events": [], "knowledge": [], "todos": []}

            events = result.get("events", [])
            knowledge = result.get("knowledge", [])
            todos = result.get("todos", [])

            logger.info(
                f"提取完成: {len(events)} events, "
                f"{len(knowledge)} knowledge, {len(todos)} todos"
            )

            return {
                "events": events,
                "knowledge": knowledge,
                "todos": todos
            }

        except Exception as e:
            logger.error(f"提取失败: {e}", exc_info=True)
            return {"events": [], "knowledge": [], "todos": []}

    async def _build_extraction_messages(
        self,
        records: List[RawRecord],
        input_usage_hint: str
    ) -> List[Dict[str, Any]]:
        """
        构建提取消息（包含系统prompt、用户prompt、截图）

        Args:
            records: 记录列表
            input_usage_hint: 键鼠活动提示

        Returns:
            消息列表
        """
        # 获取系统prompt
        system_prompt = self.prompt_manager.get_system_prompt("event_extraction")

        # 获取用户prompt模板并格式化
        user_prompt = self.prompt_manager.get_user_prompt(
            "event_extraction",
            "user_prompt_template",
            input_usage_hint=input_usage_hint
        )

        # 构建内容（文字 + 截图）
        content_items = []

        # 添加用户prompt文本
        content_items.append({
            "type": "text",
            "text": user_prompt
        })

        # 添加截图
        screenshot_count = 0
        max_screenshots = 20
        for record in records:
            if record.type == RecordType.SCREENSHOT_RECORD and screenshot_count < max_screenshots:
                is_first_image = screenshot_count == 0
                img_data = self._get_record_image_data(record, is_first=is_first_image)
                if img_data:
                    content_items.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_data}"
                        }
                    })
                    screenshot_count += 1

        logger.debug(f"构建提取消息: {screenshot_count} 张截图")

        # 构建完整消息
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": content_items
            }
        ]

        return messages

    def _get_record_image_data(self, record: RawRecord, *, is_first: bool = False) -> Optional[str]:
        """获取截图记录的base64数据并执行必要的压缩"""
        try:
            data = record.data or {}
            # 直接读取记录中携带的base64
            img_data = data.get("img_data")
            if img_data:
                return self._optimize_image_base64(img_data, is_first=is_first)
            img_hash = data.get("hash")
            if not img_hash:
                return None

            # 优先从内存缓存读取
            cached = self.image_manager.get_from_memory_cache(img_hash)
            if cached:
                return self._optimize_image_base64(cached, is_first=is_first)

            # 回退读取缩略图
            thumbnail = self.image_manager.load_thumbnail_base64(img_hash)
            if thumbnail:
                return self._optimize_image_base64(thumbnail, is_first=is_first)
            return None
        except Exception as e:
            logger.debug(f"获取截图数据失败: {e}")
            return None

    def _optimize_image_base64(self, base64_data: str, *, is_first: bool) -> str:
        """对base64图片数据执行压缩优化"""
        if not base64_data or not self.image_optimizer:
            return base64_data

        try:
            img_bytes = base64.b64decode(base64_data)
            optimized_bytes, meta = self.image_optimizer.optimize(img_bytes, is_first=is_first)

            if optimized_bytes and optimized_bytes != img_bytes:
                logger.debug(
                    "EventSummarizer: 图像压缩完成 "
                    f"{meta.get('original_tokens', 0)} → {meta.get('optimized_tokens', 0)} tokens"
                )
            return base64.b64encode(optimized_bytes).decode("utf-8")
        except Exception as exc:
            logger.debug(f"EventSummarizer: 图像压缩失败，使用原图: {exc}")
            return base64_data

    # ============ 兼容旧接口 ============

    async def summarize_events(self, records: List[RawRecord]) -> str:
        """
        兼容旧版 EventSummarizer 的事件汇总接口
        使用事件提取结果构造简要摘要
        """
        if not records:
            return "无事件"

        try:
            cache_key = f"{records[0].timestamp.isoformat()}-{len(records)}"
            if cache_key in self._summary_cache:
                return self._summary_cache[cache_key]

            extraction = await self.extract_event_knowledge_todo(records)
            events = extraction.get("events", [])

            if not events:
                summary = "暂无可总结事件"
            else:
                lines = []
                for idx, event in enumerate(events, start=1):
                    title = (event.get("title") or f"事件{idx}").strip()
                    description = (event.get("description") or "").strip()
                    if description:
                        lines.append(f"{idx}. {title} - {description}")
                    else:
                        lines.append(f"{idx}. {title}")
                summary = "\n".join(lines)

            self._summary_cache[cache_key] = summary
            return summary

        except Exception as exc:
            logger.error(f"事件总结失败: {exc}")
            return "事件总结失败"

    # ============ Activity聚合 ============

    async def aggregate_events_to_activities(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        聚合events为activities

        Args:
            events: event列表

        Returns:
            activity列表
        """
        if not events:
            return []

        try:
            logger.info(f"开始聚合 {len(events)} 个events为activities")

            # 构建events JSON（带index）
            events_with_index = [
                {
                    "index": i + 1,
                    "title": event["title"],
                    "description": event["description"]
                }
                for i, event in enumerate(events)
            ]
            events_json = json.dumps(events_with_index, ensure_ascii=False, indent=2)

            # 构建消息
            messages = self.prompt_manager.build_messages(
                "activity_aggregation",
                "user_prompt_template",
                events_json=events_json
            )

            # 获取配置参数
            config_params = self.prompt_manager.get_config_params("activity_aggregation")

            # 调用LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # 解析JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"聚合结果格式错误: {content[:200]}")
                return []

            activities_data = result.get("activities", [])

            # 转换为完整的activity对象
            activities = []
            for activity_data in activities_data:
                # 解析source indexes
                source_indexes = activity_data.get("source", [])

                # 确保indexes是字符串列表
                if isinstance(source_indexes, list):
                    source_event_ids = []
                    for idx in source_indexes:
                        try:
                            idx_int = int(idx)
                            if 0 < idx_int <= len(events):
                                source_event_ids.append(events[idx_int - 1]["id"])
                        except (ValueError, KeyError):
                            continue
                else:
                    source_event_ids = []

                # 计算时间范围
                source_events = []
                for idx in source_indexes:
                    try:
                        idx_int = int(idx)
                        if 0 < idx_int <= len(events):
                            source_events.append(events[idx_int - 1])
                    except ValueError:
                        continue

                if not source_events:
                    continue

                # 获取时间戳
                start_time = None
                end_time = None
                for e in source_events:
                    timestamp = e.get("timestamp")
                    if timestamp:
                        if isinstance(timestamp, str):
                            timestamp = datetime.fromisoformat(timestamp)
                        if start_time is None or timestamp < start_time:
                            start_time = timestamp
                        if end_time is None or timestamp > end_time:
                            end_time = timestamp

                if not start_time:
                    start_time = datetime.now()
                if not end_time:
                    end_time = start_time

                activity = {
                    "id": str(uuid.uuid4()),
                    "title": activity_data.get("title", "未命名活动"),
                    "description": activity_data.get("description", ""),
                    "start_time": start_time,
                    "end_time": end_time,
                    "source_event_ids": source_event_ids,
                    "created_at": datetime.now()
                }

                activities.append(activity)

            logger.info(f"聚合完成: 生成 {len(activities)} 个activities")
            return activities

        except Exception as e:
            logger.error(f"聚合activities失败: {e}", exc_info=True)
            return []

    # ============ Knowledge合并 ============

    async def merge_knowledge(
        self,
        knowledge_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并knowledge为combined_knowledge

        Args:
            knowledge_list: knowledge列表

        Returns:
            combined_knowledge列表
        """
        if not knowledge_list or len(knowledge_list) < 2:
            logger.debug("Knowledge数量不足，跳过合并")
            return []

        try:
            logger.info(f"开始合并 {len(knowledge_list)} 个knowledge")

            # 构建knowledge列表JSON
            knowledge_json = json.dumps(knowledge_list, ensure_ascii=False, indent=2)

            # 构建消息
            messages = self.prompt_manager.build_messages(
                "knowledge_merge",
                "user_prompt_template",
                knowledge_list=knowledge_json
            )

            # 获取配置参数
            config_params = self.prompt_manager.get_config_params("knowledge_merge")

            # 调用LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # 解析JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"合并结果格式错误: {content[:200]}")
                return []

            combined_list = result.get("combined_knowledge", [])

            # 添加ID和时间戳
            for combined in combined_list:
                combined["id"] = str(uuid.uuid4())
                combined["created_at"] = datetime.now()
                # 确保merged_from_ids存在
                if "merged_from_ids" not in combined:
                    combined["merged_from_ids"] = []

            logger.info(f"合并完成: 生成 {len(combined_list)} 个combined_knowledge")
            return combined_list

        except Exception as e:
            logger.error(f"合并knowledge失败: {e}", exc_info=True)
            return []

    # ============ Todo合并 ============

    async def merge_todos(
        self,
        todo_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并todos为combined_todos

        Args:
            todo_list: todo列表

        Returns:
            combined_todos列表
        """
        if not todo_list or len(todo_list) < 2:
            logger.debug("Todo数量不足，跳过合并")
            return []

        try:
            logger.info(f"开始合并 {len(todo_list)} 个todos")

            # 构建todo列表JSON
            todo_json = json.dumps(todo_list, ensure_ascii=False, indent=2)

            # 构建消息
            messages = self.prompt_manager.build_messages(
                "todo_merge",
                "user_prompt_template",
                todo_list=todo_json
            )

            # 获取配置参数
            config_params = self.prompt_manager.get_config_params("todo_merge")

            # 调用LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # 解析JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"合并结果格式错误: {content[:200]}")
                return []

            combined_list = result.get("combined_todos", [])

            # 添加ID、时间戳和completed状态
            for combined in combined_list:
                combined["id"] = str(uuid.uuid4())
                combined["created_at"] = datetime.now()
                combined["completed"] = False
                # 确保merged_from_ids存在
                if "merged_from_ids" not in combined:
                    combined["merged_from_ids"] = []

            logger.info(f"合并完成: 生成 {len(combined_list)} 个combined_todos")
            return combined_list

        except Exception as e:
            logger.error(f"合并todos失败: {e}", exc_info=True)
            return []

    # ============ 日记生成 ============

    async def generate_diary(
        self,
        activities: List[Dict[str, Any]],
        date: str
    ) -> str:
        """
        生成日记

        Args:
            activities: activity列表
            date: 日期（YYYY-MM-DD）

        Returns:
            日记内容（包含activity引用）
        """
        if not activities:
            return "今天没有记录到活动。" if self.language == "zh" else "No activities recorded today."

        try:
            logger.info(f"开始生成日记，共 {len(activities)} 个activities")

            # 构建activities JSON
            activities_json = json.dumps(activities, ensure_ascii=False, indent=2)

            # 构建消息
            messages = self.prompt_manager.build_messages(
                "diary_generation",
                "user_prompt_template",
                date=date,
                activities_json=activities_json
            )

            # 获取配置参数
            config_params = self.prompt_manager.get_config_params("diary_generation")

            # 调用LLM
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # 解析JSON
            result = parse_json_from_response(content)

            if isinstance(result, dict):
                diary_content = result.get("content", content)
            else:
                diary_content = content

            logger.info("日记生成完成")
            return diary_content

        except Exception as e:
            logger.error(f"生成日记失败: {e}", exc_info=True)
            error_msg = f"日记生成失败: {str(e)}" if self.language == "zh" else f"Diary generation failed: {str(e)}"
            return error_msg
