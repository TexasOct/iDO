"""
Chat 服务层
处理对话创建、消息发送、流式输出等业务逻辑

此文件在原有 ChatService 基础上增加了显式命令触发 Agent 的集成。
当用户发送以 `/task ` 开头的消息时，后端将创建并启动 Agent 任务（异步执行），
并立即在聊天中返回任务创建确认。任务执行及进度由现有的 agents.manager 负责，
前端可通过事件或 Agent API 查看任务状态与结果。
"""

import uuid
import json
import re
import textwrap
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.logger import get_logger
from core.db import get_db
from core.models import Conversation, Message, MessageRole
from core.events import emit_chat_message_chunk
from llm.client import get_llm_client

# Agent task manager
from agents.manager import task_manager

logger = get_logger(__name__)


class ChatService:
    """Chat 服务类"""

    def __init__(self):
        self.db = get_db()
        self.llm_client = get_llm_client()

    async def create_conversation(
        self,
        title: str,
        related_activity_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        创建新对话
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.now()

        metadata = (metadata or {}).copy()
        metadata.setdefault("autoTitle", True)
        metadata.setdefault("titleFinalized", False)
        metadata.setdefault("generatedTitleSource", "default")

        conversation = Conversation(
            id=conversation_id,
            title=title,
            created_at=now,
            updated_at=now,
            related_activity_ids=related_activity_ids or [],
            metadata=metadata or {}
        )

        # 保存到数据库
        self.db.insert_conversation(
            conversation_id=conversation.id,
            title=conversation.title,
            related_activity_ids=conversation.related_activity_ids,
            metadata=conversation.metadata
        )

        logger.info(f"✅ 创建对话成功: {conversation_id}, 标题: {title}")
        return conversation

    async def create_conversation_from_activities(
        self,
        activity_ids: List[str]
    ) -> Dict[str, Any]:
        """
        从活动创建对话，并生成上下文
        """
        if not activity_ids:
            raise ValueError("活动 ID 列表不能为空")

        # TODO: 从数据库获取活动详情
        activities = []  # placeholder, keep original behavior

        title = "关于活动的讨论"
        if activities:
            title = f"关于 {activities[0].get('title', '活动')} 的讨论"

        conversation = await self.create_conversation(
            title=title,
            related_activity_ids=activity_ids,
            metadata={
                "autoTitle": False,
                "titleFinalized": True,
                "generatedTitleSource": "activity_seed"
            }
        )

        context_prompt = self._generate_activity_context_prompt(activities)

        await self.save_message(
            conversation_id=conversation.id,
            role="system",
            content=context_prompt
        )

        return {
            "conversationId": conversation.id,
            "title": title,
            "context": context_prompt
        }

    async def _load_activity_context(
        self,
        activity_ids: List[str]
    ) -> Optional[str]:
        """
        从数据库加载活动详情并生成上下文
        """
        if not activity_ids:
            logger.warning("⚠️ activity_ids 为空，无法加载活动上下文")
            return None

        try:
            logger.info(f"🔍 开始加载活动上下文，活动ID: {activity_ids}")

            activities = []
            for activity_id in activity_ids:
                activity_data = self.db.execute_query(
                    "SELECT * FROM activities WHERE id = ?",
                    (activity_id,)
                )
                if activity_data:
                    activities.append(activity_data[0])
                    logger.debug(f"  ✅ 找到活动: {activity_data[0].get('title', 'Unknown')}")
                else:
                    logger.warning(f"  ⚠️ 未找到活动 ID: {activity_id}")

            if not activities:
                logger.warning("⚠️ 未找到任何活动数据")
                return None

            context_parts = ["# 活动上下文\n\n用户正在讨论以下活动，请基于这些活动信息进行分析和回答：\n"]

            for activity in activities:
                title = activity.get("title", "未命名活动")
                description = activity.get("description", "")
                start_time = activity.get("start_time", "")
                end_time = activity.get("end_time", "")

                context_parts.append(f"\n## 活动：{title}\n")
                context_parts.append(f"- **时间范围**: {start_time} - {end_time}\n")

                if description:
                    context_parts.append(f"- **描述**: {description}\n")

                source_events_json = activity.get("source_events", "[]")
                source_events = json.loads(source_events_json) if isinstance(source_events_json, str) else source_events_json

                if source_events:
                    context_parts.append(f"- **事件数量**: {len(source_events)} 个事件摘要\n")
                    context_parts.append("- **关键事件**:\n")

                    for event in source_events[:5]:
                        event_title = event.get("title", "未命名事件")
                        event_summary = event.get("summary", "")
                        context_parts.append(f"  - {event_title}")
                        if event_summary:
                            context_parts.append(f": {event_summary}")
                        context_parts.append("\n")

                    if len(source_events) > 5:
                        context_parts.append(f"  - ... 还有 {len(source_events) - 5} 个事件\n")

            context_parts.append("\n请基于以上活动信息回答用户的问题。\n")

            context_str = "".join(context_parts)
            logger.info(f"✅ 成功生成活动上下文，长度: {len(context_str)} 字符")
            logger.debug(f"上下文内容预览: {context_str[:200]}...")

            return context_str

        except Exception as e:
            logger.error(f"❌ 加载活动上下文失败: {e}", exc_info=True)
            return None

    def _generate_activity_context_prompt(
        self,
        activities: List[Dict[str, Any]]
    ) -> str:
        """
        生成活动上下文 prompt
        """
        if not activities:
            return "用户希望讨论最近的活动。"

        prompt_parts = ["用户在以下时间段进行了这些活动：\n"]

        for activity in activities:
            start_time = activity.get("start_time", "未知")
            end_time = activity.get("end_time", "未知")
            title = activity.get("title", "未命名活动")
            description = activity.get("description", "")

            prompt_parts.append(f"\n[{start_time} - {end_time}] {title}")
            if description:
                prompt_parts.append(f"  {description}")

        prompt_parts.append("\n\n请根据这些活动提供分析和建议。")

        return "\n".join(prompt_parts)

    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        保存消息到数据库
        """
        message_id = str(uuid.uuid4())
        now = datetime.now()

        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=MessageRole(role),
            content=content,
            timestamp=now,
            metadata=metadata or {}
        )

        # 保存到数据库
        self.db.insert_message(
            message_id=message.id,
            conversation_id=message.conversation_id,
            role=message.role.value,
            content=message.content,
            timestamp=message.timestamp.isoformat(),
            metadata=message.metadata
        )

        # 更新对话的 updated_at
        self.db.update_conversation(
            conversation_id=conversation_id,
            title=None  # 不更新标题
        )

        logger.debug(f"保存消息: {message_id}, 对话: {conversation_id}, 角色: {role}")
        return message

    async def get_message_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取对话的消息历史（用于LLM上下文）
        """
        messages = self.db.get_messages(conversation_id, limit=limit)

        llm_messages = []
        for msg in messages:
            llm_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # 如果消息很少（首次对话），检查是否有关联的活动，注入上下文
        if len(llm_messages) <= 2:
            logger.debug(f"🔍 检查对话 {conversation_id} 是否有关联活动（消息数: {len(llm_messages)}）")
            conversation_data = self.db.get_conversation_by_id(conversation_id)

            if not conversation_data:
                logger.warning(f"⚠️ 未找到对话数据: {conversation_id}")
            elif not conversation_data.get("related_activity_ids"):
                logger.debug(f"📝 对话 {conversation_id} 没有关联活动")
            else:
                activity_ids = json.loads(conversation_data["related_activity_ids"]) \
                    if isinstance(conversation_data["related_activity_ids"], str) \
                    else conversation_data["related_activity_ids"]

                logger.info(f"🔗 对话 {conversation_id} 关联了活动: {activity_ids}")

                if activity_ids:
                    activity_context = await self._load_activity_context(activity_ids)
                    if activity_context:
                        context_message = {
                            "role": "system",
                            "content": activity_context
                        }
                        llm_messages.insert(0, context_message)
                        logger.info(f"✅ 为对话 {conversation_id} 注入活动上下文，活动数量: {len(activity_ids)}，上下文长度: {len(activity_context)}")
                    else:
                        logger.warning("⚠️ 无法生成活动上下文")

        return llm_messages

    # ===== Agent related helpers =====

    def _detect_agent_command(self, user_message: Optional[str]) -> Optional[str]:
        """
        检测用户消息是否为显式 Agent 命令（以 '/task' 开头）。
        返回任务描述（去掉前缀）或 None。
        """
        if not user_message:
            return None
        text = user_message.strip()
        if text.startswith("/task"):
            desc = text[len("/task"):].strip()
            return desc if desc else None
        return None

    def _select_agent_type(self, task_description: str) -> str:
        """
        简单关键词规则来决定应该使用哪个 Agent。
        以后可替换为更复杂的意图检测/分类逻辑。
        """
        low = (task_description or "").lower()
        if any(k in low for k in ["写", "文章", "文档", "博客", "报告", "写作"]):
            return "WritingAgent"
        if any(k in low for k in ["研究", "收集", "资料", "调研", "调查"]):
            return "ResearchAgent"
        if any(k in low for k in ["分析", "统计", "数据", "趋势", "评估"]):
            return "AnalysisAgent"
        return "SimpleAgent"

    async def _handle_agent_task_and_respond(self, conversation_id: str, task_desc: str) -> str:
        """
        创建 Agent 任务并启动执行，返回要发送到 chat 的确认文本。
        任务实际在后台执行，前端可通过 Agent API 或事件查看进度与结果。
        """
        agent_type = self._select_agent_type(task_desc)
        try:
            task = task_manager.create_task(agent_type, task_desc)
            logger.info(f"Chat -> 创建 Agent 任务: {task.id} agent={agent_type} desc={task_desc}")

            started = await task_manager.execute_task(task.id)
            if started:
                reply = (
                    f"已创建任务 `{task.id}`，由 `{agent_type}` 执行。"
                    " 任务已在后台启动，你可以在“任务”页面查看进度与结果。"
                )
            else:
                reply = "任务创建/启动失败，请稍后重试。"
        except Exception as e:
            logger.error(f"Chat -> 创建/启动 Agent 任务失败: {e}", exc_info=True)
            reply = f"任务创建失败：{str(e)[:200]}"

        # 保存 assistant 的确认回复并通过流式事件发回（一次性完成）
        try:
            await self.save_message(conversation_id=conversation_id, role="assistant", content=reply)
        except Exception:
            logger.exception("保存任务确认消息失败")
        try:
            emit_chat_message_chunk(conversation_id=conversation_id, chunk=reply, done=True)
        except Exception:
            logger.exception("发送任务确认事件失败")

        return reply

    async def send_message_stream(
        self,
        conversation_id: str,
        user_message: str
    ) -> str:
        """
        发送消息并流式返回响应

        支持：
        - 普通 LLM 聊天流（原有逻辑）
        - 显式 Agent 命令：消息以 `/task` 开头时，创建并启动 Agent 任务，立即返回确认（并保存为 assistant 消息）。
        """
        # 1. 保存用户消息
        await self.save_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message
        )
        self._maybe_update_conversation_title(conversation_id)

        # 1.a 检测是否为 Agent 命令（/task）
        task_desc = self._detect_agent_command(user_message)
        if task_desc is not None:
            logger.info(f"检测到 /task 命令，任务描述: {task_desc}")
            return await self._handle_agent_task_and_respond(conversation_id, task_desc)

        # 2. 获取历史消息（可能包含活动上下文）
        messages = await self.get_message_history(conversation_id)

        logger.debug(f"📝 对话 {conversation_id} 消息数量: {len(messages)}")
        if messages:
            logger.debug(f"📝 第一条消息角色: {messages[0].get('role')}, 内容长度: {len(messages[0].get('content', ''))}")

        # 2.5 如果消息列表为空或第一条不是系统消息，添加 Markdown 格式指导
        if not messages or messages[0].get("role") != "system":
            system_prompt = {
                "role": "system",
                "content": (
                    "你是一个专业的 AI 助手。请使用 Markdown 格式回复，注意：\n"
                    "- 使用 `代码` 表示行内代码（单个反引号）\n"
                    "- 使用 ```语言\\n代码块\\n``` 表示多行代码块（三个反引号）\n"
                    "- 使用 **粗体** 表示强调\n"
                    "- 使用 - 或 1. 表示列表\n"
                    "- 不要在普通文本中使用反引号字符，除非是表示代码"
                )
            }
            messages.insert(0, system_prompt)
            logger.debug("📝 添加 Markdown 格式指导系统消息")

        # 记录发送给 LLM 的消息
        logger.info(f"🤖 发送给 LLM 的消息数量: {len(messages)}")
        for i, msg in enumerate(messages):
            logger.debug(f"  消息 {i}: role={msg.get('role')}, 内容长度={len(msg.get('content', ''))}")

        # 3. 流式调用 LLM
        full_response = ""
        try:
            async for chunk in self.llm_client.chat_completion_stream(messages):
                full_response += chunk

                # 实时发送到前端
                emit_chat_message_chunk(
                    conversation_id=conversation_id,
                    chunk=chunk,
                    done=False
                )

            # 4. 保存完整的 assistant 回复
            assistant_message = await self.save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response
            )
            self._maybe_update_conversation_title(conversation_id)

            # 5. 发送完成信号
            emit_chat_message_chunk(
                conversation_id=conversation_id,
                chunk="",
                done=True,
                message_id=assistant_message.id
            )

            logger.info(f"✅ 流式消息发送完成: {conversation_id}, 长度: {len(full_response)}")
            return full_response

        except Exception as e:
            logger.error(f"流式消息发送失败: {e}", exc_info=True)

            # 发送错误信号
            error_message = f"[错误] {str(e)[:100]}"
            emit_chat_message_chunk(
                conversation_id=conversation_id,
                chunk=error_message,
                done=True
            )

            # 保存错误消息
            await self.save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=error_message,
                metadata={"error": True}
            )

            raise

    async def get_conversations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """
        获取对话列表
        """
        conversations_data = self.db.get_conversations(limit=limit, offset=offset)

        conversations = []
        for data in conversations_data:
            import json
            from datetime import timezone

            # SQLite CURRENT_TIMESTAMP 返回 UTC 时间，需要明确指定为 UTC
            created_at = datetime.fromisoformat(data["created_at"]).replace(tzinfo=timezone.utc)
            updated_at = datetime.fromisoformat(data["updated_at"]).replace(tzinfo=timezone.utc)

            conversation = Conversation(
                id=data["id"],
                title=data["title"],
                created_at=created_at,
                updated_at=updated_at,
                related_activity_ids=json.loads(data.get("related_activity_ids", "[]")),
                metadata=json.loads(data.get("metadata", "{}"))
            )
            conversations.append(conversation)

        return conversations

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """
        获取对话的消息列表
        """
        messages_data = self.db.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )

        messages = []
        for data in messages_data:
            import json
            from datetime import timezone

            # SQLite 存储的时间戳是 UTC，需要明确指定为 UTC
            timestamp = datetime.fromisoformat(data["timestamp"]).replace(tzinfo=timezone.utc)

            message = Message(
                id=data["id"],
                conversation_id=data["conversation_id"],
                role=MessageRole(data["role"]),
                content=data["content"],
                timestamp=timestamp,
                metadata=json.loads(data.get("metadata", "{}"))
            )
            messages.append(message)

        return messages

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除对话（级联删除消息）
        """
        affected_rows = self.db.delete_conversation(conversation_id)
        if affected_rows > 0:
            logger.info(f"✅ 删除对话成功: {conversation_id}")
            return True
        else:
            logger.warning(f"删除对话失败（不存在）: {conversation_id}")
            return False

    # ===== 工具方法 =====

    def _maybe_update_conversation_title(self, conversation_id: str) -> None:
        """根据首条消息自动生成标题"""
        try:
            conversation = self.db.get_conversation_by_id(conversation_id)
            if not conversation:
                return

            current_title = (conversation.get("title") or "").strip()
            metadata_raw = conversation.get("metadata") or "{}"
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                metadata = {}

            if not metadata.get("autoTitle", True) or metadata.get("titleFinalized"):
                return

            messages = self.db.get_messages(conversation_id, limit=10, offset=0)

            candidate_text = ""
            for msg in messages:
                text = (msg.get("content") or "").strip()
                if not text:
                    continue
                if msg.get("role") == "user":
                    candidate_text = text
                    break

            if not candidate_text:
                for msg in messages:
                    text = (msg.get("content") or "").strip()
                    if text:
                        candidate_text = text
                        break

            new_title = self._generate_title_from_text(candidate_text)
            if not new_title or new_title == current_title:
                return

            metadata["autoTitle"] = False
            metadata["titleFinalized"] = True
            metadata["generatedTitleSource"] = "auto"
            metadata["generatedTitlePreview"] = new_title
            metadata["generatedTitleAt"] = datetime.now().isoformat()

            self.db.update_conversation(
                conversation_id=conversation_id,
                title=new_title,
                metadata=metadata
            )

            logger.info(f"自动生成对话标题: {conversation_id} -> {new_title}")
        except Exception as exc:
            logger.warning(f"自动更新对话标题失败: {exc}")

    def _generate_title_from_text(self, text: str, max_length: int = 28) -> str:
        """从文本中提取简短标题"""
        if not text:
            return ""

        cleaned = text.strip()
        cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        cleaned = re.sub(r"^[#>*\-\s]+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_")

        if not cleaned:
            return ""

        if len(cleaned) <= max_length:
            return cleaned

        return textwrap.shorten(cleaned, width=max_length, placeholder="…")


# 全局服务实例
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """获取 Chat 服务实例"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
