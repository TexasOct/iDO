"""
Chat 服务层
处理对话创建、消息发送、流式输出等业务逻辑
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

        Args:
            title: 对话标题
            related_activity_ids: 关联的活动 ID 列表
            metadata: 额外元数据

        Returns:
            Conversation: 创建的对话对象
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

        Args:
            activity_ids: 活动 ID 列表

        Returns:
            Dict: 包含对话 ID 和上下文的字典
        """
        if not activity_ids:
            raise ValueError("活动 ID 列表不能为空")

        # TODO: 从数据库获取活动详情
        # 这里先使用简化逻辑，后续需要实现完整的活动查询
        activities = []  # await self.db.get_activities_by_ids(activity_ids)

        # 生成对话标题
        title = f"关于活动的讨论"
        if activities:
            title = f"关于 {activities[0].get('title', '活动')} 的讨论"

        # 创建对话
        conversation = await self.create_conversation(
            title=title,
            related_activity_ids=activity_ids,
            metadata={
                "autoTitle": False,
                "titleFinalized": True,
                "generatedTitleSource": "activity_seed"
            }
        )

        # 生成上下文 prompt
        context_prompt = self._generate_activity_context_prompt(activities)

        # 插入系统消息（上下文）
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

    def _generate_activity_context_prompt(
        self,
        activities: List[Dict[str, Any]]
    ) -> str:
        """
        生成活动上下文 prompt

        Args:
            activities: 活动列表

        Returns:
            str: 上下文 prompt
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

        Args:
            conversation_id: 对话 ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            metadata: 额外元数据

        Returns:
            Message: 保存的消息对象
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

        Args:
            conversation_id: 对话 ID
            limit: 最大消息数量

        Returns:
            List[Dict]: LLM 格式的消息列表
        """
        messages = self.db.get_messages(conversation_id, limit=limit)

        # 转换为 LLM 格式
        llm_messages = []
        for msg in messages:
            llm_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        return llm_messages

    async def send_message_stream(
        self,
        conversation_id: str,
        user_message: str
    ) -> str:
        """
        发送消息并流式返回响应

        Args:
            conversation_id: 对话 ID
            user_message: 用户消息内容

        Returns:
            str: 完整的 assistant 回复（用于保存）
        """
        # 1. 保存用户消息
        await self.save_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message
        )
        self._maybe_update_conversation_title(conversation_id)

        # 2. 获取历史消息
        messages = await self.get_message_history(conversation_id)

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

        Args:
            limit: 最大数量
            offset: 偏移量

        Returns:
            List[Conversation]: 对话列表
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

        Args:
            conversation_id: 对话 ID
            limit: 最大数量
            offset: 偏移量

        Returns:
            List[Message]: 消息列表
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

        Args:
            conversation_id: 对话 ID

        Returns:
            bool: 是否删除成功
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
