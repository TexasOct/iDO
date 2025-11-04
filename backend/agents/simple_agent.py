"""
Simple agent implementations
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from core.models import AgentTask, AgentTaskStatus, AgentConfig
from core.logger import get_logger
from llm.client import get_llm_client
from .base import BaseAgent, TaskResult

logger = get_logger(__name__)


class SimpleAgent(BaseAgent):
    """Simple agent implementation"""

    def __init__(self, agent_type: str = "SimpleAgent"):
        super().__init__(agent_type)
        self.llm_client = get_llm_client()

    def can_handle(self, task: AgentTask) -> bool:
        """Determine if this task can be handled"""
        # Simple agent can handle all tasks
        return True

    async def execute(self, task: AgentTask) -> TaskResult:
        """Execute task"""
        try:
            logger.info(f"Starting task execution: {task.id} - {task.plan_description}")

            # Build prompt
            messages = [
                {
                    "role": "system",
                    "content": "You are a general intelligent assistant, good at handling various tasks. Please provide detailed solutions and results according to user needs.",
                },
                {
                    "role": "user",
                    "content": f"Task: {task.plan_description}\n\nPlease analyze this task and provide detailed execution plan and results.",
                },
            ]

            # Call LLM
            result = await self.llm_client.chat_completion(messages)
            content = result.get("content", "Task execution failed")

            logger.info(f"Task execution completed: {task.id}")

            return TaskResult(
                success=True,
                message="Task executed successfully",
                data={
                    "result": {"type": "text", "content": content},
                    "execution_time": 0,
                },
            )

        except Exception as e:
            logger.error(
                f"Task execution failed: {task.id}, error: {str(e)}", exc_info=True
            )
            return TaskResult(
                success=False, message=f"Task execution failed: {str(e)}", data={}
            )


class WritingAgent(SimpleAgent):
    """Writing assistant agent"""

    def __init__(self):
        super().__init__("WritingAgent")

    def can_handle(self, task: AgentTask) -> bool:
        """Determine if this writing-related task can be handled"""
        writing_keywords = [
            "write",
            "article",
            "document",
            "blog",
            "report",
            "summary",
            "content",
        ]
        return any(keyword in task.plan_description for keyword in writing_keywords)

    async def execute(self, task: AgentTask) -> TaskResult:
        """Execute writing task"""
        try:
            logger.info(f"Writing assistant starting task execution: {task.id}")

            messages = [
                {
                    "role": "system",
                    "content": "You are a professional writing assistant, good at writing various types of documents, articles and reports. Please provide high-quality writing content according to user needs.",
                },
                {
                    "role": "user",
                    "content": f"Writing task: {task.plan_description}\n\nPlease provide detailed writing plan and content outline.",
                },
            ]

            result = await self.llm_client.chat_completion(messages)
            content = result.get("content", "Writing task execution failed")

            await asyncio.sleep(3)  # Writing tasks need more time

            return TaskResult(
                success=True,
                message="Writing task completed",
                data={
                    "result": {"type": "text", "content": content},
                    "execution_time": 3,
                },
            )

        except Exception as e:
            logger.error(f"Writing task execution failed: {task.id}, error: {str(e)}")
            return TaskResult(
                success=False,
                message=f"Writing task execution failed: {str(e)}",
                data={},
            )


class ResearchAgent(SimpleAgent):
    """Research assistant agent"""

    def __init__(self):
        super().__init__("ResearchAgent")

    def can_handle(self, task: AgentTask) -> bool:
        """Determine if this research-related task can be handled"""
        research_keywords = [
            "research",
            "collect",
            "materials",
            "investigate",
            "analyze",
            "survey",
            "search",
        ]
        return any(keyword in task.plan_description for keyword in research_keywords)

    async def execute(self, task: AgentTask) -> TaskResult:
        """Execute research task"""
        try:
            logger.info(f"Research assistant starting task execution: {task.id}")

            messages = [
                {
                    "role": "system",
                    "content": "You are a professional research assistant, good at collecting, organizing and analyzing various information. Please provide detailed research plans and results according to user needs.",
                },
                {
                    "role": "user",
                    "content": f"Research task: {task.plan_description}\\n\\nPlease provide detailed research plan and expected results.",
                },
            ]

            result = await self.llm_client.chat_completion(messages)
            content = result.get("content", "Research task execution failed")

            await asyncio.sleep(4)  # Research tasks need more time

            return TaskResult(
                success=True,
                message="Research task completed",
                data={
                    "result": {"type": "text", "content": content},
                    "execution_time": 4,
                },
            )

        except Exception as e:
            logger.error(f"Research task execution failed: {task.id}, error: {str(e)}")
            return TaskResult(
                success=False,
                message=f"Research task execution failed: {str(e)}",
                data={},
            )


class AnalysisAgent(SimpleAgent):
    """Analysis assistant agent"""

    def __init__(self):
        super().__init__("AnalysisAgent")

    def can_handle(self, task: AgentTask) -> bool:
        """Determine if this analysis-related task can be handled"""
        analysis_keywords = [
            "analyze",
            "statistics",
            "data",
            "trend",
            "report",
            "evaluate",
            "compare",
        ]
        return any(keyword in task.plan_description for keyword in analysis_keywords)

    async def execute(self, task: AgentTask) -> TaskResult:
        """Execute analysis task"""
        try:
            logger.info(f"Analysis assistant starting task execution: {task.id}")

            messages = [
                {
                    "role": "system",
                    "content": "You are a professional data analysis assistant, good at analyzing various data and trends. Please provide detailed analysis plans and results according to user needs.",
                },
                {
                    "role": "user",
                    "content": f"Analysis task: {task.plan_description}\\n\\nPlease provide detailed analysis plan and expected results.",
                },
            ]

            result = await self.llm_client.chat_completion(messages)
            content = result.get("content", "Analysis task execution failed")

            await asyncio.sleep(3)  # Analysis tasks need some time

            return TaskResult(
                success=True,
                message="Analysis task completed",
                data={
                    "result": {"type": "text", "content": content},
                    "execution_time": 3,
                },
            )

        except Exception as e:
            logger.error(f"Analysis task execution failed: {task.id}, error: {str(e)}")
            return TaskResult(
                success=False,
                message=f"Analysis task execution failed: {str(e)}",
                data={},
            )


# Available agent configurations
AVAILABLE_AGENTS = [
    AgentConfig(
        name="SimpleAgent",
        description="General intelligent assistant, handles various tasks",
        icon="🤖",
    ),
    AgentConfig(
        name="WritingAgent",
        description="Writing assistant, helps write documents and articles",
        icon="📝",
    ),
    AgentConfig(
        name="ResearchAgent",
        description="Research assistant, helps collect and organize materials",
        icon="🔍",
    ),
    AgentConfig(
        name="AnalysisAgent",
        description="Analysis assistant, helps data analysis and summary",
        icon="📊",
    ),
]
