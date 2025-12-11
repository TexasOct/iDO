"""
Diary Agent - Encapsulates diary generation logic

Unlike TodoAgent and KnowledgeAgent, DiaryAgent is simpler since diary generation
is user-triggered (not automatic). It provides a clean interface for diary generation.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.settings import get_settings
from llm.manager import get_llm_manager
from llm.prompt_manager import get_prompt_manager

logger = get_logger(__name__)


class DiaryAgent:
    """Diary generation agent

    Encapsulates diary generation logic without periodic background tasks.
    Diary generation is user-triggered via API endpoints.
    """

    def __init__(self):
        """
        Initialize DiaryAgent
        """
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()
        self.is_running = False

        # Statistics
        self.stats: Dict[str, Any] = {
            "diaries_generated": 0,
            "last_generation_time": None,
        }

    def _get_language(self) -> str:
        """Get current language setting from config with caching"""
        return self.settings.get_language()

    async def start(self):
        """Start diary agent (no background tasks needed)"""
        if self.is_running:
            logger.warning("DiaryAgent is already running")
            return

        self.is_running = True
        logger.info("DiaryAgent started")

    async def stop(self):
        """Stop diary agent"""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("DiaryAgent stopped")

    async def generate_diary(
        self, date: str, activities: List[Dict[str, Any]], enable_supervisor: bool = True
    ) -> Optional[str]:
        """
        Generate diary content using LLM

        Args:
            date: Date in YYYY-MM-DD format
            activities: List of activities for the date
            enable_supervisor: Whether to enable supervisor validation (default True)

        Returns:
            Generated diary content string, or None if generation fails
        """
        try:
            logger.debug(f"Generating diary for {date} with {len(activities)} activities")

            # Get current language from settings
            language = self._get_language()
            prompt_manager = get_prompt_manager(language)

            # Format activities as JSON for the prompt
            activities_json = json.dumps(activities, ensure_ascii=False, indent=2)

            # Build messages using prompt manager
            messages = prompt_manager.build_messages(
                "diary_generation", date=date, activities_json=activities_json
            )

            # Get config parameters
            config_params = prompt_manager.get_config_params("diary_generation")

            # Call LLM
            response = await self.llm_manager.chat_completion(
                messages=messages,
                max_tokens=config_params.get("max_tokens", 4000),
                temperature=config_params.get("temperature", 0.8),
            )

            if not response or not response.get("content"):
                raise ValueError("LLM response is empty")

            raw_content = response["content"].strip()

            # Try to parse JSON response
            try:
                parsed = parse_json_from_response(raw_content)
                if isinstance(parsed, dict) and parsed.get("content"):
                    diary_content = str(parsed["content"]).strip()
                else:
                    # Fallback to raw content if JSON doesn't have expected structure
                    diary_content = raw_content
            except Exception as e:
                logger.debug(f"Failed to parse JSON diary response, using raw content: {e}")
                diary_content = raw_content

            # Record token usage to dashboard
            try:
                from core.dashboard.manager import get_dashboard_manager

                dashboard = get_dashboard_manager()
                model_info = self.llm_manager.get_active_model_info()
                model_name = model_info.get("model", "unknown")
                dashboard.record_llm_request(
                    model=model_name,
                    prompt_tokens=response.get("prompt_tokens", 0),
                    completion_tokens=response.get("completion_tokens", 0),
                    total_tokens=response.get("total_tokens", 0),
                    cost=response.get("cost", 0.0),
                    request_type="diary_generation",
                )
            except Exception as e:
                logger.debug(f"Failed to record LLM usage: {e}")

            # Apply supervisor validation if enabled
            if enable_supervisor and diary_content:
                diary_content = await self._validate_with_supervisor(diary_content)

            # Update statistics
            self.stats["diaries_generated"] += 1
            self.stats["last_generation_time"] = datetime.now()

            logger.debug(f"Diary generation completed for {date}")
            return diary_content

        except Exception as e:
            logger.error(f"Failed to generate diary: {e}", exc_info=True)
            return None

    async def _validate_with_supervisor(self, diary_content: str) -> str:
        """
        Validate diary content with supervisor

        Args:
            diary_content: Original diary content

        Returns:
            Validated/revised diary content
        """
        try:
            from agents.supervisor import DiarySupervisor

            language = self._get_language()
            supervisor = DiarySupervisor(language=language)

            result = await supervisor.validate(diary_content)

            # Log validation results
            if not result.is_valid:
                logger.warning(
                    f"DiarySupervisor found {len(result.issues)} issues: {result.issues}"
                )
                if result.suggestions:
                    logger.info(f"DiarySupervisor suggestions: {result.suggestions}")

            # Use revised content if available, otherwise use original
            validated_content = (
                result.revised_content if result.revised_content else diary_content
            )

            logger.debug(
                f"DiaryAgent: Supervisor validated diary ({len(diary_content)} → {len(validated_content)} chars)"
            )

            return validated_content

        except Exception as e:
            logger.error(f"DiaryAgent: Supervisor validation failed: {e}", exc_info=True)
            # On supervisor failure, return original content
            return diary_content

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information

        Returns:
            Statistics dictionary
        """
        return {
            "is_running": self.is_running,
            "language": self._get_language(),
            "stats": {
                "diaries_generated": self.stats["diaries_generated"],
                "last_generation_time": self.stats["last_generation_time"].isoformat()
                if self.stats["last_generation_time"]
                else None,
            },
        }
