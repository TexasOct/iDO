"""
Supervisor - Quality validation for agent outputs
Provides review and validation for TODO, Knowledge, and Diary generation
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from core.logger import get_logger
from core.json_parser import parse_json_from_response
from llm.manager import get_llm_manager
from llm.prompt_manager import get_prompt_manager

logger = get_logger(__name__)


class SupervisorResult:
    """Result from supervisor validation"""

    def __init__(
        self,
        is_valid: bool,
        issues: List[str],
        suggestions: List[str],
        revised_content: Optional[Any] = None,
    ):
        """
        Initialize supervisor result

        Args:
            is_valid: Whether the content passes validation
            issues: List of identified issues
            suggestions: List of improvement suggestions
            revised_content: Optional revised version of the content
        """
        self.is_valid = is_valid
        self.issues = issues
        self.suggestions = suggestions
        self.revised_content = revised_content

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "is_valid": self.is_valid,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "revised_content": self.revised_content,
        }


class BaseSupervisor(ABC):
    """Base class for content supervisors"""

    def __init__(self, language: str = "zh"):
        """
        Initialize supervisor

        Args:
            language: Language setting (zh | en)
        """
        self.language = language
        self.llm_manager = get_llm_manager()
        self.prompt_manager = get_prompt_manager(language)

    @abstractmethod
    async def validate(self, content: Any, **kwargs: Any) -> SupervisorResult:
        """
        Validate content

        Args:
            content: Content to validate
            **kwargs: Additional context for validation (subclass-specific)

        Returns:
            SupervisorResult with validation results
        """
        pass

    async def _call_llm_for_validation(
        self, prompt_category: str, content_json: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Call LLM for validation

        Args:
            prompt_category: Category in prompt configuration
            content_json: JSON string of content to validate
            **kwargs: Additional template variables (e.g., source_events_section, source_actions_section)

        Returns:
            Parsed validation result
        """
        try:
            # Build messages with additional template variables
            template_vars = {"content_json": content_json}
            template_vars.update(kwargs)

            messages = self.prompt_manager.build_messages(
                prompt_category, "user_prompt_template", **template_vars
            )

            # Get configuration parameters
            config_params = self.prompt_manager.get_config_params(prompt_category)

            # Call LLM
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"Supervisor returned invalid format: {content[:200]}")
                return {}

            return result

        except Exception as e:
            logger.error(f"Supervisor validation failed: {e}", exc_info=True)
            return {}


class TodoSupervisor(BaseSupervisor):
    """Supervisor for TODO items"""

    async def validate(self, content: List[Dict[str, Any]], **kwargs: Any) -> SupervisorResult:
        """
        Validate TODO items

        Args:
            content: List of TODO items to validate
            **kwargs: Additional context (unused)

        Returns:
            SupervisorResult with validation results
        """
        if not content:
            return SupervisorResult(
                is_valid=True, issues=[], suggestions=[], revised_content=content
            )

        try:
            import json

            todos_json = json.dumps(content, ensure_ascii=False, indent=2, default=str)

            # Call LLM for validation
            result = await self._call_llm_for_validation(
                "todo_supervisor", todos_json
            )

            if not result:
                # Validation failed, but don't block
                return SupervisorResult(
                    is_valid=True,
                    issues=["Supervisor validation unavailable"],
                    suggestions=[],
                    revised_content=content,
                )

            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            revised_todos = result.get("revised_todos", content)

            logger.debug(
                f"TodoSupervisor: valid={is_valid}, issues={len(issues)}, suggestions={len(suggestions)}"
            )

            return SupervisorResult(
                is_valid=is_valid,
                issues=issues,
                suggestions=suggestions,
                revised_content=revised_todos,
            )

        except Exception as e:
            logger.error(f"TodoSupervisor validation error: {e}", exc_info=True)
            return SupervisorResult(
                is_valid=True,
                issues=[f"Validation error: {str(e)}"],
                suggestions=[],
                revised_content=content,
            )


class KnowledgeSupervisor(BaseSupervisor):
    """Supervisor for Knowledge items"""

    async def validate(self, content: List[Dict[str, Any]], **kwargs: Any) -> SupervisorResult:
        """
        Validate knowledge items

        Args:
            content: List of knowledge items to validate
            **kwargs: Additional context (unused)

        Returns:
            SupervisorResult with validation results
        """
        if not content:
            return SupervisorResult(
                is_valid=True,
                issues=[],
                suggestions=[],
                revised_content=content,
            )

        try:
            import json

            knowledge_json = json.dumps(content, ensure_ascii=False, indent=2, default=str)

            # Call LLM for validation
            result = await self._call_llm_for_validation(
                "knowledge_supervisor", knowledge_json
            )

            if not result:
                # Validation failed, but don't block
                return SupervisorResult(
                    is_valid=True,
                    issues=["Supervisor validation unavailable"],
                    suggestions=[],
                    revised_content=content,
                )

            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            revised_knowledge = result.get("revised_knowledge", content)

            logger.debug(
                f"KnowledgeSupervisor: valid={is_valid}, issues={len(issues)}, suggestions={len(suggestions)}"
            )

            return SupervisorResult(
                is_valid=is_valid,
                issues=issues,
                suggestions=suggestions,
                revised_content=revised_knowledge,
            )

        except Exception as e:
            logger.error(f"KnowledgeSupervisor validation error: {e}", exc_info=True)
            return SupervisorResult(
                is_valid=True,
                issues=[f"Validation error: {str(e)}"],
                suggestions=[],
                revised_content=content,
            )


class DiarySupervisor(BaseSupervisor):
    """Supervisor for Diary entries"""

    async def validate(self, content: str, **kwargs: Any) -> SupervisorResult:
        """
        Validate diary content

        Args:
            content: Diary text to validate
            **kwargs: Additional context (unused)

        Returns:
            SupervisorResult with validation results
        """
        if not content or not content.strip():
            return SupervisorResult(
                is_valid=False,
                issues=["Empty diary content"],
                suggestions=["Generate meaningful diary content"],
                revised_content=content,
            )

        try:
            import json

            content_json = json.dumps(
                {"content": content}, ensure_ascii=False, indent=2
            )

            # Call LLM for validation
            result = await self._call_llm_for_validation(
                "diary_supervisor", content_json
            )

            if not result:
                # Validation failed, but don't block
                return SupervisorResult(
                    is_valid=True,
                    issues=["Supervisor validation unavailable"],
                    suggestions=[],
                    revised_content=content,
                )

            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            revised_content = result.get("revised_content", content)

            logger.debug(
                f"DiarySupervisor: valid={is_valid}, issues={len(issues)}, suggestions={len(suggestions)}"
            )

            return SupervisorResult(
                is_valid=is_valid,
                issues=issues,
                suggestions=suggestions,
                revised_content=revised_content,
            )

        except Exception as e:
            logger.error(f"DiarySupervisor validation error: {e}", exc_info=True)
            return SupervisorResult(
                is_valid=True,
                issues=[f"Validation error: {str(e)}"],
                suggestions=[],
                revised_content=content,
            )


class EventSupervisor(BaseSupervisor):
    """Supervisor for Event items"""

    async def validate(
        self,
        content: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> SupervisorResult:
        """
        Validate event items

        Args:
            content: List of event items to validate
            **kwargs: Additional context
                - source_actions: Optional list of source actions for semantic validation

        Returns:
            SupervisorResult with validation results
        """
        source_actions = kwargs.get("source_actions")

        if not content:
            return SupervisorResult(
                is_valid=True, issues=[], suggestions=[], revised_content=content
            )

        try:
            import json

            events_json = json.dumps(content, ensure_ascii=False, indent=2, default=str)

            # Build source actions section if provided
            source_actions_section = ""
            if source_actions:
                source_actions_json = json.dumps(
                    source_actions, ensure_ascii=False, indent=2, default=str
                )
                source_actions_section = f"""
【Source Actions for Semantic Validation】
The following are the source actions that were aggregated into the events above.
Use these to verify that event titles and descriptions accurately reflect the underlying actions:

{source_actions_json}
"""

            # Call LLM for validation
            result = await self._call_llm_for_validation(
                "event_supervisor",
                events_json,
                source_actions_section=source_actions_section,
            )

            if not result:
                # Validation failed, but don't block
                return SupervisorResult(
                    is_valid=True,
                    issues=["Supervisor validation unavailable"],
                    suggestions=[],
                    revised_content=content,
                )

            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            revised_events = result.get("revised_events", content)

            logger.debug(
                f"EventSupervisor: valid={is_valid}, issues={len(issues)}, suggestions={len(suggestions)}"
            )

            return SupervisorResult(
                is_valid=is_valid,
                issues=issues,
                suggestions=suggestions,
                revised_content=revised_events,
            )

        except Exception as e:
            logger.error(f"EventSupervisor validation error: {e}", exc_info=True)
            return SupervisorResult(
                is_valid=True,
                issues=[f"Validation error: {str(e)}"],
                suggestions=[],
                revised_content=content,
            )


class ActivitySupervisor(BaseSupervisor):
    """Supervisor for Activity items"""

    async def validate(
        self,
        content: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> SupervisorResult:
        """
        Validate activity items

        Args:
            content: List of activity items to validate
            **kwargs: Additional context
                - source_events: Optional list of source events for semantic validation

        Returns:
            SupervisorResult with validation results
        """
        source_events = kwargs.get("source_events")

        if not content:
            return SupervisorResult(
                is_valid=True, issues=[], suggestions=[], revised_content=content
            )

        try:
            import json
            from datetime import datetime

            activities_json = json.dumps(content, ensure_ascii=False, indent=2, default=str)

            # Build source events section if provided
            source_events_section = ""
            if source_events:
                # Enrich events with duration for better analysis
                enriched_events = []
                for event in source_events:
                    event_copy = event.copy()
                    start = event.get("start_time")
                    end = event.get("end_time")

                    if start and end:
                        # Calculate duration
                        if isinstance(start, str):
                            start = datetime.fromisoformat(start)
                        if isinstance(end, str):
                            end = datetime.fromisoformat(end)

                        duration = (end - start).total_seconds()
                        event_copy["duration_seconds"] = int(duration)
                        event_copy["duration_display"] = self._format_duration(
                            duration
                        )

                    enriched_events.append(event_copy)

                source_events_json = json.dumps(
                    enriched_events, ensure_ascii=False, indent=2, default=str
                )
                source_events_section = f"""
【Source Events for Semantic Validation】
The following are the source events that were aggregated into the activities above.
Each event includes its duration. Use these to:
1. Calculate time distribution across different themes
2. Identify the dominant theme (most time spent)
3. Verify that activity titles reflect the dominant theme, not minor topics

{source_events_json}
"""

            # Call LLM for validation
            result = await self._call_llm_for_validation(
                "activity_supervisor",
                activities_json,
                source_events_section=source_events_section,
            )

            if not result:
                # Validation failed, but don't block
                return SupervisorResult(
                    is_valid=True,
                    issues=["Supervisor validation unavailable"],
                    suggestions=[],
                    revised_content=content,
                )

            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            revised_activities = result.get("revised_activities", content)

            logger.debug(
                f"ActivitySupervisor: valid={is_valid}, issues={len(issues)}, suggestions={len(suggestions)}"
            )

            return SupervisorResult(
                is_valid=is_valid,
                issues=issues,
                suggestions=suggestions,
                revised_content=revised_activities,
            )

        except Exception as e:
            logger.error(f"ActivitySupervisor validation error: {e}", exc_info=True)
            return SupervisorResult(
                is_valid=True,
                issues=[f"Validation error: {str(e)}"],
                suggestions=[],
                revised_content=content,
            )

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable format"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

