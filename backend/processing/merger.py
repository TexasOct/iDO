"""
Activity merging logic
Use LLM to determine if new events are related to existing activities, decide to merge or create new activity
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
    """Activity merger"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
        self.prompt_manager = get_prompt_manager()
        self.merge_threshold = 0.7  # Similarity threshold
        self.time_threshold = 300  # Activities within 5 minutes may be related

    async def merge_activity_with_event(
        self,
        current_activity: Activity,
        new_event: Event,
        merged_title: str = "",
        merged_description: str = "",
    ) -> Dict[str, Any]:
        """Merge single event into current activity"""
        try:
            # Update activity information
            merged_activity = current_activity.copy()

            # Update end time
            merged_activity["end_time"] = new_event.end_time

            # Add new event
            if "source_events" not in merged_activity:
                merged_activity["source_events"] = []

            merged_activity["source_events"].append(new_event)

            # Update event count
            merged_activity["event_count"] = len(merged_activity["source_events"])

            # Use LLM-provided merged title and description, generate if not available
            if merged_title and merged_description:
                merged_activity["title"] = merged_title
                merged_activity["description"] = merged_description
            else:
                result = await self._generate_merged_description_with_llm(
                    current_activity.get("description", ""), new_event.summary
                )
                merged_activity["title"] = result.get(
                    "title", current_activity.get("title", "")
                )
                merged_activity["description"] = result.get("description", "")

            logger.info(f"Event merged into activity: {merged_activity['id']}")
            return merged_activity

        except Exception as e:
            logger.error(f"Failed to merge event: {e}")
            return current_activity

    def _is_within_time_threshold(
        self, current_activity: Dict[str, Any], new_events: List[RawRecord]
    ) -> bool:
        """Check if within time threshold"""
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

    async def _llm_judge_merge(
        self, current_activity: Dict[str, Any], new_event: Event
    ) -> Tuple[bool, str, str]:
        """Use LLM to determine whether activities should be merged

        Returns:
            (should_merge, merged_title, merged_description): Whether to merge, merged title and description
        """
        try:
            # Get description of current activity
            current_summary = current_activity.get("description", "")

            # Get summary of new event
            new_summary = new_event.summary

            if not current_summary or not new_summary:
                logger.warning(
                    "Unable to get activity or event summary, defaulting to no merge"
                )
                return False, "", ""

            # Build LLM prompt
            messages = self.prompt_manager.build_messages(
                "activity_merging.merge_judgment",
                "user_prompt_template",
                current_summary=current_summary,
                new_summary=new_summary,
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params(
                "activity_merging", "merge_judgment"
            )
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "")

            # Parse JSON returned by LLM
            should_merge, merged_title, merged_description = self._parse_merge_judgment(
                content
            )

            logger.debug(f"LLM judgment result: {content}")
            return should_merge, merged_title, merged_description

        except Exception as e:
            logger.error(f"LLM activity merge judgment failed: {e}")
            return False, "", ""

    def _get_current_activity_summary(self, current_activity: Dict[str, Any]) -> str:
        """Get summary of current activity"""
        try:
            # Get summary of the last event from source_events of current activity
            source_events = current_activity.get("source_events", [])
            if not source_events:
                return current_activity.get("description", "")

            # Get summary of the last event
            last_event = source_events[-1]
            if hasattr(last_event, "summary"):
                return last_event.summary
            else:
                return current_activity.get("description", "")

        except Exception as e:
            logger.error(f"Failed to get current activity summary: {e}")
            return current_activity.get("description", "")

    async def _get_new_events_summary(self, new_events: List[RawRecord]) -> str:
        """Get summary of new events"""
        try:
            if not new_events:
                return ""

            # Use summarizer to generate summary of new events
            from .summarizer import EventSummarizer

            summarizer = EventSummarizer(self.llm_client)

            summary = await summarizer.summarize_events(new_events)
            return summary

        except Exception as e:
            logger.error(f"Failed to get new events summary: {e}")
            return ""

    def _build_merge_judgment_prompt(
        self, current_summary: str, new_summary: str
    ) -> str:
        """Build merge judgment prompt (deprecated, now uses prompts.toml configuration)"""
        return f"""
Please determine whether the following two user activities should be merged into the same activity:

**Current Activity Description:**
{current_summary}

**New Activity Description:**
{new_summary}

Please adopt a lenient merge strategy, considering the following factors (meeting any one can consider merging):
1. Whether activities are related or similar (even if not exactly the same)
2. Whether activities are performed in the same application or website
3. Whether activities might belong to the same overall workflow or task
4. Whether the themes or goals of the activities are related
5. Whether there is natural continuity between activities

**Merge Guidance Principles:**
- Prioritize merging unless the two activities are clearly unrelated
- Similar activities should be merged (e.g., browsing different pages on the same website, editing different files in the same application)
- Related topic activities should be merged (e.g., research → coding, tutorial → practice)
- Only completely unrelated activities should be separated (e.g., coding → watching entertainment videos)

Please return your judgment result in JSON format:
{{
    "should_merge": true/false,
    "reason": "Judgment reason",
    "merged_description": "If merging, please provide the merged activity description, summarized in one or two sentences"
}}

Where:
- should_merge: Whether to merge (boolean value)
- reason: Brief judgment reason
- merged_description: If should_merge is true, provide the merged activity description; if false, can be empty string
"""

    def _parse_merge_judgment(self, content: str) -> Tuple[bool, str, str]:
        """Parse merge judgment result returned by LLM

        Returns:
            (should_merge, merged_title, merged_description): Whether to merge, merged title and description
        """
        try:
            # 使用通用JSON解析工具
            result = parse_json_from_response(content)

            if result is None:
                logger.warning(
                    f"Unable to parse JSON from LLM response: {content[:200]}..."
                )
                return False, "", ""

            # 验证必需字段
            if not isinstance(result, dict):
                logger.warning(f"LLM returned is not a JSON object: {type(result)}")
                return False, "", ""

            should_merge = result.get("should_merge", False)
            merged_title = result.get("merged_title", "")
            merged_description = result.get("merged_description", "")

            logger.debug(
                f"Parsing LLM judgment: should_merge={should_merge}, title={merged_title}"
            )
            return should_merge, merged_title, merged_description

        except Exception as e:
            logger.error(f"Failed to parse LLM merge judgment: {e}")
            return False, "", ""

    async def _generate_merged_description(self, activity: Dict[str, Any]) -> str:
        """Generate merged activity description"""
        try:
            # Simple description generation logic
            event_count = activity.get("event_count", 0)
            if event_count == 0:
                return "Empty activity"

            time_span = 0
            start_time = activity.get("start_time")
            end_time = activity.get("end_time")

            if start_time and end_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time)
                time_span = (end_time - start_time).total_seconds()

            description_parts = ["Activity"]

            if time_span > 0:
                if time_span > 60:
                    description_parts.append(f"duration {time_span / 60:.1f} minutes")
                else:
                    description_parts.append(f"duration {time_span:.1f} seconds")

            description_parts.append(f"contains {event_count} events")

            return " - ".join(description_parts)

        except Exception as e:
            logger.error(f"Failed to generate merged description: {e}")
            return "Merged activity"

    async def _generate_merged_description_with_llm(
        self, current_description: str, new_event_summary: str
    ) -> Dict[str, str]:
        """Use LLM to generate merged activity title and description

        Returns:
            Dictionary containing title and description
        """
        try:
            messages = self.prompt_manager.build_messages(
                "activity_merging.merge_description",
                "user_prompt_template",
                current_description=current_description,
                new_event_summary=new_event_summary,
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params(
                "activity_merging", "merge_description"
            )
            response = await self.llm_client.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Use universal JSON parsing tool
            result = parse_json_from_response(content)

            if result is not None and isinstance(result, dict):
                title = result.get("title", "")
                description = result.get("description", "")

                if title and description:
                    logger.debug(
                        f"Generated merge result: title={title}, description={description}"
                    )
                    return {"title": title, "description": description}

            # If LLM did not return valid JSON, use simple merge
            logger.warning(
                f"LLM did not return valid JSON, using simple merge. Original response: {content[:200]}..."
            )
            merged_description = f"{current_description} | {new_event_summary}"
            # Don't truncate title, use complete merged_description
            merged_title = merged_description
            return {"title": merged_title, "description": merged_description}

        except Exception as e:
            logger.error(f"Failed to generate merged description: {e}")
            # Fallback to simple merge
            merged_description = f"{current_description} | {new_event_summary}"
            # Don't truncate title, use complete merged_description
            merged_title = merged_description
            return {"title": merged_title, "description": merged_description}

    def set_merge_threshold(self, threshold: float):
        """Set merge threshold"""
        self.merge_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Activity merge threshold set to: {self.merge_threshold}")

    def set_time_threshold(self, threshold: int):
        """Set time threshold (seconds)"""
        self.time_threshold = max(0, threshold)
        logger.info(f"Activity time threshold set to: {self.time_threshold} seconds")
