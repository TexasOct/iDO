"""
Chat service layer
Handles business logic for conversation creation, message sending, streaming output, etc.

This file adds explicit command-triggered Agent integration based on the original ChatService.
When users send messages starting with `/task `, the backend will create and start Agent tasks (asynchronous execution),
and immediately return task creation confirmation in the chat. Task execution and progress are handled by the existing agents.manager,
the frontend can view task status and results through events or Agent API.
"""

import asyncio
import base64
import json
import os
import re
import textwrap
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Agent task manager
from agents.manager import task_manager
from core.db import get_db
from core.events import emit_chat_message_chunk
from core.logger import get_logger
from core.models import Conversation, Message, MessageRole
from core.protocols import ChatDatabaseProtocol
from llm.manager import get_llm_manager

from .chat_stream_manager import get_stream_manager

logger = get_logger(__name__)


class ChatService:
    """Chat 服务类"""

    def __init__(self):
        self.db: ChatDatabaseProtocol = get_db()
        self.llm_manager = get_llm_manager()
        self.stream_manager = get_stream_manager()

    async def create_conversation(
        self,
        title: str,
        related_activity_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
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
            metadata=metadata or {},
            model_id=model_id,
        )

        # 保存到数据库
        self.db.conversations.insert(
            conversation_id=conversation.id,
            title=conversation.title,
            related_activity_ids=conversation.related_activity_ids,
            metadata=conversation.metadata,
            model_id=model_id,
        )

        logger.info(f"✅ 创建对话成功: {conversation_id}, 标题: {title}")
        return conversation

    async def create_conversation_from_activities(
        self, activity_ids: List[str]
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
                "generatedTitleSource": "activity_seed",
            },
        )

        context_prompt = self._generate_activity_context_prompt(activities)

        await self.save_message(
            conversation_id=conversation.id, role="system", content=context_prompt
        )

        return {
            "conversationId": conversation.id,
            "title": title,
            "context": context_prompt,
        }

    async def _load_activity_context(self, activity_ids: List[str]) -> Optional[str]:
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
                # Use async repository method
                import asyncio
                activity_data = asyncio.run(self.db.activities.get_by_id(activity_id))
                if activity_data:
                    activities.append(activity_data)
                    logger.debug(
                        f"  ✅ 找到活动: {activity_data.get('title', 'Unknown')}"
                    )
                else:
                    logger.warning(f"  ⚠️ 未找到活动 ID: {activity_id}")

            if not activities:
                logger.warning("⚠️ 未找到任何活动数据")
                return None

            context_parts = [
                "# 活动上下文\n\n用户正在讨论以下活动，请基于这些活动信息进行分析和回答：\n"
            ]

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
                source_events = (
                    json.loads(source_events_json)
                    if isinstance(source_events_json, str)
                    else source_events_json
                )

                if source_events:
                    context_parts.append(
                        f"- **事件数量**: {len(source_events)} 个事件摘要\n"
                    )
                    context_parts.append("- **关键事件**:\n")

                    for event in source_events[:5]:
                        event_title = event.get("title", "未命名事件")
                        event_summary = event.get("summary", "")
                        context_parts.append(f"  - {event_title}")
                        if event_summary:
                            context_parts.append(f": {event_summary}")
                        context_parts.append("\n")

                    if len(source_events) > 5:
                        context_parts.append(
                            f"  - ... 还有 {len(source_events) - 5} 个事件\n"
                        )

            context_parts.append("\n请基于以上活动信息回答用户的问题。\n")

            context_str = "".join(context_parts)
            logger.info(f"✅ 成功生成活动上下文，长度: {len(context_str)} 字符")
            logger.debug(f"上下文内容预览: {context_str[:200]}...")

            return context_str

        except Exception as e:
            logger.error(f"❌ 加载活动上下文失败: {e}", exc_info=True)
            return None

    def _generate_activity_context_prompt(
        self, activities: List[Dict[str, Any]]
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
        metadata: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
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
            metadata=metadata or {},
            images=images or [],
        )

        # 保存到数据库
        self.db.messages.insert(
            message_id=message.id,
            conversation_id=message.conversation_id,
            role=message.role.value,
            content=message.content,
            timestamp=message.timestamp.isoformat(),
            metadata=message.metadata,
            images=message.images,
        )

        # 更新对话的 updated_at
        self.db.conversations.update(
            conversation_id=conversation_id,
            title=None,  # 不更新标题
        )

        logger.debug(
            f"保存消息: {message_id}, 对话: {conversation_id}, 角色: {role}, 图片数: {len(images or [])}"
        )
        return message

    async def get_message_history(
        self, conversation_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取对话的消息历史（用于LLM上下文）
        支持多模态消息（文本+图片）
        """
        messages = self.db.messages.get_by_conversation(conversation_id, limit=limit)

        llm_messages = []
        for msg in messages:
            # 检查消息是否包含图片
            images_json = msg.get("images", "[]")
            images = (
                json.loads(images_json)
                if isinstance(images_json, str)
                else images_json or []
            )

            if images:
                # 多模态消息格式 (OpenAI Vision API)
                content_parts = []

                # 添加文本内容（如果有）
                if msg["content"]:
                    content_parts.append({"type": "text", "text": msg["content"]})

                # 添加图片
                for image_data in images:
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data  # base64 格式: data:image/jpeg;base64,...
                            },
                        }
                    )

                llm_messages.append({"role": msg["role"], "content": content_parts})
            else:
                # 纯文本消息
                llm_messages.append({"role": msg["role"], "content": msg["content"]})

        # 如果消息很少（首次对话），检查是否有关联的活动，注入上下文
        if len(llm_messages) <= 2:
            logger.debug(
                f"🔍 检查对话 {conversation_id} 是否有关联活动（消息数: {len(llm_messages)}）"
            )
            conversation_data = self.db.conversations.get_by_id(conversation_id)

            if not conversation_data:
                logger.warning(f"⚠️ 未找到对话数据: {conversation_id}")
            elif not conversation_data.get("related_activity_ids"):
                logger.debug(f"📝 对话 {conversation_id} 没有关联活动")
            else:
                activity_ids = (
                    json.loads(conversation_data["related_activity_ids"])
                    if isinstance(conversation_data["related_activity_ids"], str)
                    else conversation_data["related_activity_ids"]
                )

                logger.info(f"🔗 对话 {conversation_id} 关联了活动: {activity_ids}")

                if activity_ids:
                    activity_context = await self._load_activity_context(activity_ids)
                    if activity_context:
                        context_message = {
                            "role": "system",
                            "content": activity_context,
                        }
                        llm_messages.insert(0, context_message)
                        logger.info(
                            f"✅ 为对话 {conversation_id} 注入活动上下文，活动数量: {len(activity_ids)}，上下文长度: {len(activity_context)}"
                        )
                    else:
                        logger.warning("⚠️ 无法生成活动上下文")

        return llm_messages

    # ===== Image processing helpers =====

    async def _convert_image_paths_to_base64(
        self, images: Optional[List[str]] = None
    ) -> Optional[List[str]]:
        """
        Convert image file paths to base64 encoded strings.
        Detects if an image is a file path or already base64/data URL encoded.

        Args:
            images: List of image strings (file paths or base64 data)

        Returns:
            List of base64 encoded image strings
        """
        if not images:
            return images

        processed_images = []
        for image in images:
            # Check if it's already a Data URL (starts with data:)
            if image.startswith("data:"):
                # Already a Data URL, use as-is
                processed_images.append(image)
                logger.debug("Image is already a Data URL, skipping conversion")
            # Check if it looks like a file path (absolute or relative path on filesystem)
            elif (
                ("/" in image or "\\" in image)
                and not image.startswith("http")
                and os.path.exists(image)
            ):
                # Looks like a file path that exists, try to read and convert
                try:
                    with open(image, "rb") as f:
                        file_data = f.read()
                        base64_data = base64.b64encode(file_data).decode("utf-8")
                        processed_images.append(base64_data)
                        logger.debug(f"Converted image file to base64: {image}")
                except Exception as e:
                    logger.error(f"Failed to convert image file {image}: {e}")
            else:
                # Assume it's already base64 encoded (pure base64 string)
                processed_images.append(image)
                logger.debug("Image is already base64 encoded, using as-is")

        return processed_images

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
            desc = text[len("/task") :].strip()
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

    async def _handle_agent_task_and_respond(
        self, conversation_id: str, task_desc: str
    ) -> str:
        """
        创建 Agent 任务并启动执行，返回要发送到 chat 的确认文本。
        任务实际在后台执行，前端可通过 Agent API 或事件查看进度与结果。
        """
        agent_type = self._select_agent_type(task_desc)
        try:
            task = task_manager.create_task(agent_type, task_desc)
            logger.info(
                f"Chat -> 创建 Agent 任务: {task.id} agent={agent_type} desc={task_desc}"
            )

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
            await self.save_message(
                conversation_id=conversation_id, role="assistant", content=reply
            )
        except Exception:
            logger.exception("保存任务确认消息失败")
        try:
            emit_chat_message_chunk(
                conversation_id=conversation_id, chunk=reply, done=True
            )
        except Exception:
            logger.exception("发送任务确认事件失败")

        return reply

    async def send_message_stream(
        self,
        conversation_id: str,
        user_message: str,
        images: Optional[List[str]] = None,
        model_id: Optional[str] = None,
    ) -> str:
        """
        发送消息并流式返回响应

        支持：
        - 普通 LLM 聊天流（原有逻辑）
        - 多模态消息（文本+图片）
        - 显式 Agent 命令：消息以 `/task` 开头时，创建并启动 Agent 任务，立即返回确认（并保存为 assistant 消息）。

        此方法会创建一个后台任务来处理流式输出，确保不同会话之间的流式处理互不干扰。
        """
        # 检查该会话是否已有正在运行的流式任务
        if self.stream_manager.is_streaming(conversation_id):
            logger.warning(f"会话 {conversation_id} 已有正在运行的流式任务")
            # 可以选择取消旧任务或拒绝新请求
            # 这里我们取消旧任务，开始新的
            self.stream_manager.cancel_stream(conversation_id)

        # 创建后台任务来处理流式输出
        task = asyncio.create_task(
            self._process_stream(conversation_id, user_message, images, model_id)
        )

        # 注册任务到流管理器
        self.stream_manager.register_stream(conversation_id, task)

        logger.info(f"✅ 会话 {conversation_id} 的流式任务已启动")
        return ""  # 立即返回，实际响应通过事件流式发送

    async def _process_stream(
        self,
        conversation_id: str,
        user_message: str,
        images: Optional[List[str]] = None,
        model_id: Optional[str] = None,
    ) -> None:
        """
        处理流式输出的实际逻辑（在后台任务中运行）
        """
        # 超时时间：300 秒 (5 分钟)
        TIMEOUT_SECONDS = 300

        try:
            # 处理图片：将文件路径转换为base64
            processed_images = await self._convert_image_paths_to_base64(images)

            # 1. 保存用户消息（包含图片）
            await self.save_message(
                conversation_id=conversation_id,
                role="user",
                content=user_message,
                images=processed_images,
            )
            self._maybe_update_conversation_title(conversation_id)

            # 1.a 检测是否为 Agent 命令（/task）
            task_desc = self._detect_agent_command(user_message)
            if task_desc is not None:
                logger.info(f"检测到 /task 命令，任务描述: {task_desc}")
                await self._handle_agent_task_and_respond(conversation_id, task_desc)
                return

            # 2. 获取历史消息（可能包含活动上下文）
            messages = await self.get_message_history(conversation_id)

            logger.debug(f"📝 对话 {conversation_id} 消息数量: {len(messages)}")
            if messages:
                logger.debug(
                    f"📝 第一条消息角色: {messages[0].get('role')}, 内容长度: {len(messages[0].get('content', ''))}"
                )

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
                    ),
                }
                messages.insert(0, system_prompt)
                logger.debug("📝 添加 Markdown 格式指导系统消息")

            # 记录发送给 LLM 的消息
            logger.info(f"🤖 发送给 LLM 的消息数量: {len(messages)}")
            for i, msg in enumerate(messages):
                logger.debug(
                    f"  消息 {i}: role={msg.get('role')}, 内容长度={len(msg.get('content', ''))}"
                )

            # 3. 流式调用 LLM (带超时保护)
            full_response = ""
            try:
                async with asyncio.timeout(TIMEOUT_SECONDS):
                    async for chunk in self.llm_manager.chat_completion_stream(messages, model_id=model_id):
                        full_response += chunk

                        # 实时发送到前端
                        emit_chat_message_chunk(
                            conversation_id=conversation_id, chunk=chunk, done=False
                        )
            except asyncio.TimeoutError:
                error_msg = "Request timeout, please check network connection"
                logger.error(f"❌ LLM 调用超时（{TIMEOUT_SECONDS}s）: {conversation_id}")

                # 发送超时错误
                await self.save_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=error_msg,
                    metadata={"error": True, "error_type": "timeout"},
                )
                emit_chat_message_chunk(
                    conversation_id=conversation_id, chunk="", done=True
                )
                return

            # 4. 保存完整的 assistant 回复
            assistant_message = await self.save_message(
                conversation_id=conversation_id, role="assistant", content=full_response
            )
            self._maybe_update_conversation_title(conversation_id)

            # 5. 发送完成信号
            emit_chat_message_chunk(
                conversation_id=conversation_id,
                chunk="",
                done=True,
                message_id=assistant_message.id,
            )

            logger.info(
                f"✅ 流式消息发送完成: {conversation_id}, 长度: {len(full_response)}"
            )

        except asyncio.CancelledError:
            # 任务被取消（例如用户切换到其他会话并发送新消息）
            logger.warning(f"⚠️ 会话 {conversation_id} 的流式任务被取消")
            emit_chat_message_chunk(
                conversation_id=conversation_id,
                chunk="[任务已取消]",
                done=True
            )
            raise

        except Exception as e:
            logger.error(f"流式消息发送失败: {e}", exc_info=True)

            # 发送错误信号
            error_message = f"[错误] {str(e)[:100]}"
            emit_chat_message_chunk(
                conversation_id=conversation_id, chunk=error_message, done=True
            )

            # 保存错误消息
            await self.save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=error_message,
                metadata={"error": True},
            )

    async def get_conversations(
        self, limit: int = 50, offset: int = 0
    ) -> List[Conversation]:
        """
        获取对话列表
        """
        conversations_data = self.db.conversations.get_all(limit=limit, offset=offset)

        conversations = []
        for data in conversations_data:

            # SQLite CURRENT_TIMESTAMP 返回 UTC 时间，需要明确指定为 UTC
            created_at = datetime.fromisoformat(data["created_at"]).replace(
                tzinfo=timezone.utc
            )
            updated_at = datetime.fromisoformat(data["updated_at"]).replace(
                tzinfo=timezone.utc
            )

            conversation = Conversation(
                id=data["id"],
                title=data["title"],
                created_at=created_at,
                updated_at=updated_at,
                related_activity_ids=self._ensure_json_list(
                    data.get("related_activity_ids")
                ),
                metadata=self._ensure_json_dict(data.get("metadata")),
                model_id=data.get("model_id"),
            )
            conversations.append(conversation)

        return conversations

    async def get_messages(
        self, conversation_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        """
        获取对话的消息列表
        """
        messages_data = self.db.messages.get_by_conversation(
            conversation_id=conversation_id, limit=limit, offset=offset
        )

        messages = []
        for data in messages_data:

            # SQLite 存储的时间戳是 UTC，需要明确指定为 UTC
            timestamp = datetime.fromisoformat(data["timestamp"]).replace(
                tzinfo=timezone.utc
            )

            message = Message(
                id=data["id"],
                conversation_id=data["conversation_id"],
                role=MessageRole(data["role"]),
                content=data["content"],
                timestamp=timestamp,
                metadata=self._ensure_json_dict(data.get("metadata")),
                images=self._ensure_json_list(data.get("images")),
            )
            messages.append(message)

        return messages

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除对话（级联删除消息）
        """
        affected_rows = self.db.conversations.delete(conversation_id)
        if affected_rows > 0:
            logger.info(f"✅ 删除对话成功: {conversation_id}")
            return True
        else:
            logger.warning(f"删除对话失败（不存在）: {conversation_id}")
            return False

    # ===== 工具方法 =====

    def _ensure_json_list(self, value: Any) -> List[Any]:
        """Ensure the given value is a list (decoded from JSON if needed)."""
        return self._normalize_json_field(value, list)

    def _ensure_json_dict(self, value: Any) -> Dict[str, Any]:
        """Ensure the given value is a dict (decoded from JSON if needed)."""
        return self._normalize_json_field(value, dict)

    def _normalize_json_field(self, value: Any, expected_type: type) -> Any:
        fallback = [] if expected_type is list else {}

        if value is None:
            return fallback

        if expected_type is list and isinstance(value, tuple):
            return list(value)

        if isinstance(value, expected_type):
            return value

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return fallback
            try:
                parsed = json.loads(text)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning(
                    "Failed to parse %s JSON field: %s",
                    expected_type.__name__,
                    exc,
                )
                return fallback
            if isinstance(parsed, expected_type):
                return parsed

        logger.warning(
            "Unexpected value for %s JSON field: %r (using default)",
            expected_type.__name__,
            value,
        )
        return fallback

    def _maybe_update_conversation_title(self, conversation_id: str) -> None:
        """根据首条消息自动生成标题"""
        try:
            conversation = self.db.conversations.get_by_id(conversation_id)
            if not conversation:
                return

            current_title = (conversation.get("title") or "").strip()
            metadata_raw = conversation.get("metadata") or {}
            if isinstance(metadata_raw, str):
                try:
                    metadata = json.loads(metadata_raw)
                except json.JSONDecodeError:
                    metadata = {}
            else:
                metadata = metadata_raw

            if not metadata.get("autoTitle", True) or metadata.get("titleFinalized"):
                return

            messages = self.db.messages.get_by_conversation(conversation_id, limit=10, offset=0)

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

            self.db.conversations.update(
                conversation_id=conversation_id, title=new_title, metadata=metadata
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
