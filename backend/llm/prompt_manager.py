"""
LLM Prompt Manager
Reads and manages all LLM prompt templates from YAML configuration files
"""

import yaml
import toml
from typing import Dict, Any, List, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class PromptManager:
    """Prompt manager - supports multiple languages"""

    def __init__(self, config_path: Optional[str] = None, language: str = "zh"):
        """
        Initialize Prompt manager

        Args:
            config_path: Configuration file path (optional)
            language: Language code (zh | en)
        """
        self.language = language

        if config_path is None:
            config_path = self._find_config_file(language)

        self.config_path = config_path
        self.prompts = {}
        self.config = {}
        self._load_prompts()

    def _find_config_file(self, language: str = "zh") -> str:
        """
        Find configuration file, trying multiple possible path locations
        Supports multiple languages: prompts_zh.toml, prompts_en.toml

        Args:
            language: Language code
        """
        from pathlib import Path

        # Try multiple possible path locations
        search_paths = [
            # 1. Parent directory of current file /config
            Path(__file__).parent.parent / "config",
            # 2. Current working directory / backend/config
            Path.cwd() / "backend" / "config",
            # 3. Current working directory
            Path.cwd(),
        ]

        for base_path in search_paths:
            # Prioritize language-specific configuration files
            lang_toml_path = base_path / f"prompts_{language}.toml"
            lang_yaml_path = base_path / f"prompts_{language}.yaml"

            # Alternative: generic configuration files
            toml_path = base_path / "prompts.toml"
            yaml_path = base_path / "prompts.yaml"

            if lang_toml_path.exists():
                logger.info(
                    f"Found {language} language prompts config file: {lang_toml_path}"
                )
                return str(lang_toml_path)
            elif lang_yaml_path.exists():
                logger.info(
                    f"Found {language} language prompts config file: {lang_yaml_path}"
                )
                return str(lang_yaml_path)
            elif toml_path.exists():
                logger.info(f"Found generic prompts config file: {toml_path}")
                return str(toml_path)
            elif yaml_path.exists():
                logger.info(f"Found generic prompts config file: {yaml_path}")
                return str(yaml_path)

        # If none found, return first candidate path (default location for development environment)
        default_path = search_paths[0] / f"prompts_{language}.toml"
        logger.warning(
            f"Prompts config file not found, will use default path: {default_path}"
        )
        return str(default_path)

    def _load_prompts(self):
        """Load prompt configuration"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                if self.config_path.endswith(".toml"):
                    self.config = toml.load(f)
                else:
                    self.config = yaml.safe_load(f)

            # Extract prompts section
            self.prompts = self.config.get("prompts", {})
            logger.info(f"Successfully loaded prompt configuration: {self.config_path}")

        except FileNotFoundError:
            logger.error(
                f"Prompt configuration file does not exist: {self.config_path}"
            )
            self.prompts = {}
            self.config = {}
        except (yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"Failed to parse prompt configuration file: {e}")
            self.prompts = {}
            self.config = {}
        except Exception as e:
            logger.error(f"Failed to load prompt configuration: {e}")
            self.prompts = {}
            self.config = {}

    def get_prompt(self, category: str, prompt_type: str, **kwargs) -> str:
        """
        Get prompt of specified type

        Args:
            category: Prompt category (e.g.: event_summarization, activity_merging.merge_judgment)
            prompt_type: Prompt type (e.g.: system_prompt, user_prompt_template)
            **kwargs: Parameters for formatting template

        Returns:
            Formatted prompt string
        """
        try:
            # Handle nested paths, like "activity_merging.merge_judgment"
            category_parts = category.split(".")
            category_config = self.prompts

            # Traverse nested path
            for part in category_parts:
                if isinstance(category_config, dict) and part in category_config:
                    category_config = category_config[part]
                else:
                    logger.warning(f"Prompt category not found: {category}")
                    return ""

            # Get prompt template
            if not isinstance(category_config, dict):
                logger.warning(f"Prompt category is not dictionary type: {category}")
                return ""

            prompt_template = category_config.get(prompt_type, "")

            if not prompt_template:
                logger.warning(f"Prompt not found: {category}.{prompt_type}")
                return ""

            # Format template
            if kwargs:
                try:
                    return prompt_template.format(**kwargs)
                except KeyError as e:
                    logger.error(f"Failed to format prompt, missing parameter: {e}")
                    return prompt_template
            else:
                return prompt_template

        except Exception as e:
            logger.error(f"Failed to get prompt: {e}")
            return ""

    def get_system_prompt(self, category: str) -> str:
        """Get system prompt"""
        return self.get_prompt(category, "system_prompt")

    def get_user_prompt(
        self, category: str, prompt_type: str = "user_prompt_template", **kwargs
    ) -> str:
        """Get user prompt"""
        return self.get_prompt(category, prompt_type, **kwargs)

    def build_messages(
        self, category: str, prompt_type: str = "user_prompt_template", **kwargs
    ) -> List[Dict[str, str]]:
        """
        Build complete message list

        Args:
            category: Prompt category
            prompt_type: User prompt type
            **kwargs: Parameters for formatting template

        Returns:
            Message list containing system and user messages
        """
        messages = []

        # Add system message
        system_prompt = self.get_system_prompt(category)
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add user message
        user_prompt = self.get_user_prompt(category, prompt_type, **kwargs)
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})

        return messages

    def get_config_params(
        self, category: str, prompt_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get configuration parameters for specified function

        Args:
            category: Prompt category
            prompt_type: Specific prompt type (optional)

        Returns:
            Configuration parameter dictionary
        """
        try:
            config_params = self.config.get("config", {}).get("default_params", {})

            # Get parameters for specific function
            if category in self.config.get("config", {}):
                category_params = self.config["config"][category]
                if isinstance(category_params, dict):
                    config_params.update(category_params)

            # Get parameters for specific prompt type
            if prompt_type and category in self.config.get("config", {}):
                specific_params = self.config["config"][category].get(prompt_type, {})
                if isinstance(specific_params, dict):
                    config_params.update(specific_params)

            return config_params

        except Exception as e:
            logger.error(f"Failed to get configuration parameters: {e}")
            return self.config.get("config", {}).get("default_params", {})

    def reload(self):
        """Reload configuration"""
        self._load_prompts()
        logger.info("Prompt configuration has been reloaded")

    def switch_language(self, language: str):
        """
        Switch language

        Args:
            language: New language code
        """
        if language != self.language:
            self.language = language
            self.config_path = self._find_config_file(language)
            self._load_prompts()
            logger.info(f"Switched to {language} language")


# Global prompt manager instance
_prompt_manager = None


def get_prompt_manager(language: str = "zh") -> PromptManager:
    """
    Get global prompt manager instance

    Args:
        language: Language code (zh | en)

    Returns:
        PromptManager instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager(language=language)
    elif _prompt_manager.language != language:
        # If language is different, switch language
        _prompt_manager.switch_language(language)
    return _prompt_manager


# Convenience functions
def get_event_summarization_prompt(**kwargs) -> List[Dict[str, str]]:
    """Get event summarization prompt"""
    manager = get_prompt_manager()
    return manager.build_messages("event_summarization", **kwargs)


def get_merge_judgment_prompt(
    current_summary: str, new_summary: str
) -> List[Dict[str, str]]:
    """Get merge judgment prompt"""
    manager = get_prompt_manager()
    return manager.build_messages(
        "activity_merging.merge_judgment",
        "user_prompt_template",
        current_summary=current_summary,
        new_summary=new_summary,
    )


def get_merge_description_prompt(
    current_description: str, new_event_summary: str
) -> List[Dict[str, str]]:
    """Get merge description prompt"""
    manager = get_prompt_manager()
    return manager.build_messages(
        "activity_merging.merge_description",
        "user_prompt_template",
        current_description=current_description,
        new_event_summary=new_event_summary,
    )


def get_general_summary_prompt(content: str) -> List[Dict[str, str]]:
    """Get general summary prompt"""
    manager = get_prompt_manager()
    messages = manager.build_messages("general_summary")
    if messages and len(messages) > 1:
        messages[1]["content"] = content
    return messages


def get_test_prompt() -> List[Dict[str, str]]:
    """Get test prompt"""
    manager = get_prompt_manager()
    return manager.build_messages("event_summarization", "test_user_prompt")
