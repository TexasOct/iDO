"""
活动合并逻辑
使用 LLM 判断新事件是否与现有活动相关，决定合并或创建新活动
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime
from core.models import Activity, RawRecord, Event
from core.logger import get_logger
from core.json_parser import parse_json_from_response
from llm.client import get_llm_client
from llm.prompt_manager import get_prompt_manager

logger = get_logger(__name__)


class ActivityMerger:
    """活动合并器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
        self.prompt_manager = get_prompt_manager()
        self.merge_threshold = 0.7  # 相似度阈值
        self.time_threshold = 300   # 5分钟内的活动可能相关

    async def merge_activity_with_event(self,
                                      current_activity: Activity,
                                      new_event: Event,
                                      merged_title: str = "",
                                      merged_description: str = "") -> Dict[str, Any]:
        """将单个事件合并到当前活动"""
        try:
            # 更新活动信息
            merged_activity = current_activity.copy()

            # 更新结束时间
            merged_activity["end_time"] = new_event.end_time

            # 添加新事件
            if "source_events" not in merged_activity:
                merged_activity["source_events"] = []

            merged_activity["source_events"].append(new_event)

            # 更新事件计数
            merged_activity["event_count"] = len(merged_activity["source_events"])

            # 使用LLM提供的合并title和description，如果没有则生成
            if merged_title and merged_description:
                merged_activity["title"] = merged_title
                merged_activity["description"] = merged_description
            else:
                result = await self._generate_merged_description_with_llm(
                    current_activity.get("description", ""), new_event.summary
                )
                merged_activity["title"] = result.get("title", current_activity.get("title", ""))
                merged_activity["description"] = result.get("description", "")

            logger.info(f"事件已合并到活动: {merged_activity['id']}")
            return merged_activity

        except Exception as e:
            logger.error(f"事件合并失败: {e}")
            return current_activity

    def _is_within_time_threshold(self,
                                 current_activity: Dict[str, Any],
                                 new_events: List[RawRecord]) -> bool:
        """检查是否在时间阈值内"""
        if not new_events:
            return False

        current_end_time = current_activity.get("end_time")
        if not current_end_time:
            return True

        if isinstance(current_end_time, str):
            current_end_time = datetime.fromisoformat(current_end_time)

        new_start_time = min(event.timestamp for event in new_events)
        time_diff = (new_start_time - current_end_time).total_seconds()

        return time_diff <= self.time_threshold

    async def _llm_judge_merge(self,
                              current_activity: Dict[str, Any],
                              new_event: Event) -> Tuple[bool, str, str]:
        """使用LLM判断是否应该合并活动

        Returns:
            (should_merge, merged_title, merged_description): 是否合并、合并后的标题和描述
        """
        try:
            # 获取当前活动的description
            current_summary = current_activity.get("description", "")

            # 获取新event的summary
            new_summary = new_event.summary

            if not current_summary or not new_summary:
                logger.warning("无法获取活动或事件的summary，默认不合并")
                return False, "", ""

            # 构建LLM提示
            messages = self.prompt_manager.build_messages(
                "activity_merging.merge_judgment",
                "user_prompt_template",
                current_summary=current_summary,
                new_summary=new_summary
            )

            # 获取配置参数
            config_params = self.prompt_manager.get_config_params("activity_merging", "merge_judgment")
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "")

            # 解析LLM返回的JSON
            should_merge, merged_title, merged_description = self._parse_merge_judgment(content)

            logger.debug(f"LLM判断结果: {content}")
            return should_merge, merged_title, merged_description

        except Exception as e:
            logger.error(f"LLM活动合并判断失败: {e}")
            return False, "", ""

    def _get_current_activity_summary(self, current_activity: Dict[str, Any]) -> str:
        """获取当前活动的summary"""
        try:
            # 从当前活动的source_events中获取最后一个event的summary
            source_events = current_activity.get("source_events", [])
            if not source_events:
                return current_activity.get("description", "")

            # 获取最后一个event的summary
            last_event = source_events[-1]
            if hasattr(last_event, 'summary'):
                return last_event.summary
            else:
                return current_activity.get("description", "")

        except Exception as e:
            logger.error(f"获取当前活动summary失败: {e}")
            return current_activity.get("description", "")

    async def _get_new_events_summary(self, new_events: List[RawRecord]) -> str:
        """获取新events的summary"""
        try:
            if not new_events:
                return ""

            # 使用summarizer来生成新events的summary
            from .summarizer import EventSummarizer
            summarizer = EventSummarizer(self.llm_client)

            summary = await summarizer.summarize_events(new_events)
            return summary

        except Exception as e:
            logger.error(f"获取新events summary失败: {e}")
            return ""

    def _build_merge_judgment_prompt(self, current_summary: str, new_summary: str) -> str:
        """构建合并判断的提示（已废弃，现使用prompts.toml配置）"""
        return f"""
请判断以下两个用户活动是否应该合并为同一个活动：

**当前活动描述：**
{current_summary}

**新活动描述：**
{new_summary}

请采用宽松的合并策略，考虑以下因素（满足任一即可考虑合并）：
1. 活动是否相关或相似（即使不完全相同）
2. 活动是否在同一个应用或网站中进行
3. 活动是否可能属于同一个大的工作流程或任务
4. 活动的主题或目标是否有关联
5. 活动之间是否有自然的延续性

**合并指导原则：**
- 优先选择合并，除非两个活动明显无关
- 相似的活动应该合并（比如在同一个网站浏览不同页面、在同一个应用编辑不同文件）
- 相关主题的活动应该合并（比如查资料→写代码、看教程→实践操作）
- 只有完全不相关的活动才分开（比如写代码→看视频娱乐）

请以JSON格式返回你的判断结果：
{{
    "should_merge": true/false,
    "reason": "判断理由",
    "merged_description": "如果合并，请提供合并后的活动描述，一两句话概括一下"
}}

其中：
- should_merge: 是否应该合并（布尔值）
- reason: 简短的判断理由
- merged_description: 如果should_merge为true，提供合并后的活动描述；如果为false，可以为空字符串
"""

    def _parse_merge_judgment(self, content: str) -> Tuple[bool, str, str]:
        """解析LLM返回的合并判断结果

        Returns:
            (should_merge, merged_title, merged_description): 是否合并、合并后的标题和描述
        """
        try:
            # 使用通用JSON解析工具
            result = parse_json_from_response(content)

            if result is None:
                logger.warning(f"无法从LLM响应中解析JSON: {content[:200]}...")
                return False, "", ""

            # 验证必需字段
            if not isinstance(result, dict):
                logger.warning(f"LLM返回的不是JSON对象: {type(result)}")
                return False, "", ""

            should_merge = result.get("should_merge", False)
            merged_title = result.get("merged_title", "")
            merged_description = result.get("merged_description", "")

            logger.debug(f"解析LLM判断: should_merge={should_merge}, title={merged_title}")
            return should_merge, merged_title, merged_description

        except Exception as e:
            logger.error(f"解析LLM合并判断失败: {e}")
            return False, "", ""


    async def _generate_merged_description(self, activity: Dict[str, Any]) -> str:
        """生成合并后的活动描述"""
        try:
            # 简单的描述生成逻辑
            event_count = activity.get("event_count", 0)
            if event_count == 0:
                return "空活动"

            time_span = 0
            start_time = activity.get("start_time")
            end_time = activity.get("end_time")

            if start_time and end_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time)
                time_span = (end_time - start_time).total_seconds()

            description_parts = ["活动"]

            if time_span > 0:
                if time_span > 60:
                    description_parts.append(f"持续 {time_span/60:.1f} 分钟")
                else:
                    description_parts.append(f"持续 {time_span:.1f} 秒")

            description_parts.append(f"包含 {event_count} 个事件")

            return " - ".join(description_parts)

        except Exception as e:
            logger.error(f"生成合并描述失败: {e}")
            return "合并活动"

    async def _generate_merged_description_with_llm(self,
                                                  current_description: str,
                                                  new_event_summary: str) -> Dict[str, str]:
        """使用LLM生成合并后的活动标题和描述

        Returns:
            包含title和description的字典
        """
        try:
            messages = self.prompt_manager.build_messages(
                "activity_merging.merge_description",
                "user_prompt_template",
                current_description=current_description,
                new_event_summary=new_event_summary
            )

            # 获取配置参数
            config_params = self.prompt_manager.get_config_params("activity_merging", "merge_description")
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # 使用通用JSON解析工具
            result = parse_json_from_response(content)

            if result is not None and isinstance(result, dict):
                title = result.get("title", "")
                description = result.get("description", "")

                if title and description:
                    logger.debug(f"生成合并结果: title={title}, description={description}")
                    return {"title": title, "description": description}

            # 如果LLM没有返回有效的JSON，使用简单的合并
            logger.warning(f"LLM未返回有效JSON，使用简单合并。原始响应: {content[:200]}...")
            merged_description = f"{current_description} | {new_event_summary}"
            # 不截断title，使用完整的 merged_description
            merged_title = merged_description
            return {"title": merged_title, "description": merged_description}

        except Exception as e:
            logger.error(f"生成合并描述失败: {e}")
            # 回退到简单合并
            merged_description = f"{current_description} | {new_event_summary}"
            # 不截断title，使用完整的 merged_description
            merged_title = merged_description
            return {"title": merged_title, "description": merged_description}


    def set_merge_threshold(self, threshold: float):
        """设置合并阈值"""
        self.merge_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"活动合并阈值设置为: {self.merge_threshold}")

    def set_time_threshold(self, threshold: int):
        """设置时间阈值（秒）"""
        self.time_threshold = max(0, threshold)
        logger.info(f"活动时间阈值设置为: {self.time_threshold} 秒")
