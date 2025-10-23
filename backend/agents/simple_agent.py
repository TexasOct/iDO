"""
简单的Agent实现，使用smolagents库
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from core.models import AgentTask, AgentTaskStatus, AgentConfig
from core.logger import get_logger
from llm.client import get_llm_client
from .base import BaseAgent, TaskResult
from smolagents import CodeAgent, Tool

logger = get_logger(__name__)


class SimpleAgent(BaseAgent):
    """简单的Agent实现，使用smolagents库"""
    
    def __init__(self, agent_type: str = "SimpleAgent"):
        super().__init__(agent_type)
        self.llm_client = get_llm_client()
        self._setup_smolagents()
        
    def _setup_smolagents(self):
        """设置smolagents"""
        # 创建工具
        tools = [
            self._create_text_analysis_tool(),
            self._create_summary_tool()
        ]
        
        # 创建LLM适配器
        llm_adapter = self._create_llm_adapter()
        
        # 创建smolagents CodeAgent
        self.smol_agent = CodeAgent(
            tools=tools,
            model=llm_adapter,
            max_steps=5
        )
    
    def _create_llm_adapter(self):
        """创建LLM适配器"""
        class LLMAdapter:
            def __init__(self, llm_client):
                self.llm_client = llm_client
            
            async def generate(self, messages, **kwargs):
                """适配smolagents的LLM接口"""
                result = await self.llm_client.chat_completion(messages, **kwargs)
                return result.get("content", "")
        
        return LLMAdapter(self.llm_client)
    
    def _create_text_analysis_tool(self):
        """创建文本分析工具"""
        @Tool
        def analyze_text(text: str) -> str:
            """分析文本内容，提取关键信息"""
            return f"文本分析结果：文本长度为{len(text)}字符，包含{len(text.split())}个单词"
        
        return analyze_text
    
    def _create_summary_tool(self):
        """创建总结工具"""
        @Tool
        def create_summary(content: str, max_length: int = 200) -> str:
            """创建内容总结"""
            if len(content) <= max_length:
                return content
            return content[:max_length] + "..."
        
        return create_summary
        
    def can_handle(self, task: AgentTask) -> bool:
        """判断是否能处理该任务"""
        # 简单Agent可以处理所有任务
        return True
    
    async def execute(self, task: AgentTask) -> TaskResult:
        """执行任务"""
        try:
            logger.info(f"开始执行任务: {task.id} - {task.plan_description}")
            
            # 使用smolagents执行任务
            result = await self.smol_agent.run(
                f"请帮我处理这个任务：{task.plan_description}"
            )
            
            # 模拟任务执行时间
            await asyncio.sleep(2)
            
            logger.info(f"任务执行完成: {task.id}")
            
            return TaskResult(
                success=True,
                message="任务执行成功",
                data={
                    "result": {
                        "type": "text",
                        "content": str(result)
                    },
                    "execution_time": 2
                }
            )
            
        except Exception as e:
            logger.error(f"任务执行失败: {task.id}, 错误: {str(e)}")
            return TaskResult(
                success=False,
                message=f"任务执行失败: {str(e)}",
                data={}
            )


class WritingAgent(SimpleAgent):
    """写作助手Agent"""
    
    def __init__(self):
        super().__init__("WritingAgent")
    
    def can_handle(self, task: AgentTask) -> bool:
        """判断是否能处理写作相关任务"""
        writing_keywords = ["写", "文章", "文档", "博客", "报告", "总结", "内容"]
        return any(keyword in task.plan_description for keyword in writing_keywords)
    
    async def execute(self, task: AgentTask) -> TaskResult:
        """执行写作任务"""
        try:
            logger.info(f"写作助手开始执行任务: {task.id}")
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的写作助手，擅长撰写各种类型的文档、文章和报告。请根据用户需求提供高质量的写作内容。"
                },
                {
                    "role": "user",
                    "content": f"写作任务: {task.plan_description}\n\n请提供详细的写作方案和内容大纲。"
                }
            ]
            
            result = await self.llm_client.chat_completion(messages)
            content = result.get("content", "写作任务执行失败")
            
            await asyncio.sleep(3)  # 写作任务需要更多时间
            
            return TaskResult(
                success=True,
                message="写作任务完成",
                data={
                    "result": {
                        "type": "text",
                        "content": content
                    },
                    "execution_time": 3
                }
            )
            
        except Exception as e:
            logger.error(f"写作任务执行失败: {task.id}, 错误: {str(e)}")
            return TaskResult(
                success=False,
                message=f"写作任务执行失败: {str(e)}",
                data={}
            )


class ResearchAgent(SimpleAgent):
    """研究助手Agent"""
    
    def __init__(self):
        super().__init__("ResearchAgent")
    
    def can_handle(self, task: AgentTask) -> bool:
        """判断是否能处理研究相关任务"""
        research_keywords = ["研究", "收集", "资料", "调研", "分析", "调查", "查找"]
        return any(keyword in task.plan_description for keyword in research_keywords)
    
    async def execute(self, task: AgentTask) -> TaskResult:
        """执行研究任务"""
        try:
            logger.info(f"研究助手开始执行任务: {task.id}")
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的研究助手，擅长收集、整理和分析各种信息。请根据用户需求提供详细的研究方案和结果。"
                },
                {
                    "role": "user",
                    "content": f"研究任务: {task.plan_description}\n\n请提供详细的研究方案和预期结果。"
                }
            ]
            
            result = await self.llm_client.chat_completion(messages)
            content = result.get("content", "研究任务执行失败")
            
            await asyncio.sleep(4)  # 研究任务需要更多时间
            
            return TaskResult(
                success=True,
                message="研究任务完成",
                data={
                    "result": {
                        "type": "text",
                        "content": content
                    },
                    "execution_time": 4
                }
            )
            
        except Exception as e:
            logger.error(f"研究任务执行失败: {task.id}, 错误: {str(e)}")
            return TaskResult(
                success=False,
                message=f"研究任务执行失败: {str(e)}",
                data={}
            )


class AnalysisAgent(SimpleAgent):
    """分析助手Agent"""
    
    def __init__(self):
        super().__init__("AnalysisAgent")
    
    def can_handle(self, task: AgentTask) -> bool:
        """判断是否能处理分析相关任务"""
        analysis_keywords = ["分析", "统计", "数据", "趋势", "报告", "评估", "比较"]
        return any(keyword in task.plan_description for keyword in analysis_keywords)
    
    async def execute(self, task: AgentTask) -> TaskResult:
        """执行分析任务"""
        try:
            logger.info(f"分析助手开始执行任务: {task.id}")
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的数据分析助手，擅长分析各种数据和趋势。请根据用户需求提供详细的分析方案和结果。"
                },
                {
                    "role": "user",
                    "content": f"分析任务: {task.plan_description}\n\n请提供详细的分析方案和预期结果。"
                }
            ]
            
            result = await self.llm_client.chat_completion(messages)
            content = result.get("content", "分析任务执行失败")
            
            await asyncio.sleep(3)  # 分析任务需要一定时间
            
            return TaskResult(
                success=True,
                message="分析任务完成",
                data={
                    "result": {
                        "type": "text",
                        "content": content
                    },
                    "execution_time": 3
                }
            )
            
        except Exception as e:
            logger.error(f"分析任务执行失败: {task.id}, 错误: {str(e)}")
            return TaskResult(
                success=False,
                message=f"分析任务执行失败: {str(e)}",
                data={}
            )


# 可用的Agent配置
AVAILABLE_AGENTS = [
    AgentConfig(
        name="SimpleAgent",
        description="通用智能助手，使用smolagents库处理各种任务",
        icon="🤖"
    ),
    AgentConfig(
        name="WritingAgent",
        description="写作助手，帮助撰写文档和文章",
        icon="📝"
    ),
    AgentConfig(
        name="ResearchAgent", 
        description="研究助手，帮助收集和整理资料",
        icon="🔍"
    ),
    AgentConfig(
        name="AnalysisAgent",
        description="分析助手，帮助数据分析和总结",
        icon="📊"
    )
]
