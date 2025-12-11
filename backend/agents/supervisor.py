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
    async def validate(self, content: Any) -> SupervisorResult:
        """
        Validate content

        Args:
            content: Content to validate

        Returns:
            SupervisorResult with validation results
        """
        pass

    async def _call_llm_for_validation(
        self, prompt_category: str, content_json: str
    ) -> Dict[str, Any]:
        """
        Call LLM for validation

        Args:
            prompt_category: Category in prompt configuration
            content_json: JSON string of content to validate

        Returns:
            Parsed validation result
        """
        try:
            # Build messages
            messages = self.prompt_manager.build_messages(
                prompt_category, "user_prompt_template", content_json=content_json
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

    async def validate(self, todos: List[Dict[str, Any]]) -> SupervisorResult:
        """
        Validate TODO items

        Args:
            todos: List of TODO items to validate

        Returns:
            SupervisorResult with validation results
        """
        if not todos:
            return SupervisorResult(
                is_valid=True, issues=[], suggestions=[], revised_content=todos
            )

        try:
            import json

            todos_json = json.dumps(todos, ensure_ascii=False, indent=2)

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
                    revised_content=todos,
                )

            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            revised_todos = result.get("revised_todos", todos)

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
                revised_content=todos,
            )


class KnowledgeSupervisor(BaseSupervisor):
    """Supervisor for Knowledge items"""

    async def validate(self, knowledge_list: List[Dict[str, Any]]) -> SupervisorResult:
        """
        Validate knowledge items

        Args:
            knowledge_list: List of knowledge items to validate

        Returns:
            SupervisorResult with validation results
        """
        if not knowledge_list:
            return SupervisorResult(
                is_valid=True,
                issues=[],
                suggestions=[],
                revised_content=knowledge_list,
            )

        try:
            import json

            knowledge_json = json.dumps(knowledge_list, ensure_ascii=False, indent=2)

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
                    revised_content=knowledge_list,
                )

            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            revised_knowledge = result.get("revised_knowledge", knowledge_list)

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
                revised_content=knowledge_list,
            )


class DiarySupervisor(BaseSupervisor):
    """Supervisor for Diary entries"""

    async def validate(self, diary_content: str) -> SupervisorResult:
        """
        Validate diary content

        Args:
            diary_content: Diary text to validate

        Returns:
            SupervisorResult with validation results
        """
        if not diary_content or not diary_content.strip():
            return SupervisorResult(
                is_valid=False,
                issues=["Empty diary content"],
                suggestions=["Generate meaningful diary content"],
                revised_content=diary_content,
            )

        try:
            import json

            content_json = json.dumps(
                {"content": diary_content}, ensure_ascii=False, indent=2
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
                    revised_content=diary_content,
                )

            is_valid = result.get("is_valid", True)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            revised_content = result.get("revised_content", diary_content)

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
                revised_content=diary_content,
            )
