"""
Friendly Chat Service
Generates friendly, humorous chat messages based on recent user activities
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from core.logger import get_logger
from core.settings import get_settings
from core.db import get_db
from core.events import _emit
from llm.client import get_llm_client
from llm.prompt_manager import get_prompt_manager
from core.json_parser import parse_json_from_response

logger = get_logger(__name__)


class FriendlyChatService:
    """Service for generating friendly chat messages based on user activity"""

    def __init__(self):
        self.settings = get_settings()
        self.db = get_db()
        self.llm_client = None  # Will be initialized when needed
        self.prompt_manager = get_prompt_manager("zh")  # Default to Chinese
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the friendly chat scheduler"""
        if self._running:
            logger.warning("Friendly chat service already running")
            return

        chat_settings = self.settings.get_friendly_chat_settings()
        if not chat_settings.get("enabled", False):
            logger.info("Friendly chat is disabled, not starting service")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(
            f"✓ Friendly chat service started (interval: {chat_settings['interval']} min)"
        )

    async def stop(self):
        """Stop the friendly chat scheduler"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("✓ Friendly chat service stopped")

    async def _run_scheduler(self):
        """Main scheduler loop"""
        while self._running:
            try:
                chat_settings = self.settings.get_friendly_chat_settings()

                # Check if still enabled
                if not chat_settings.get("enabled", False):
                    logger.info("Friendly chat disabled, stopping service")
                    break

                interval_minutes = chat_settings.get("interval", 20)

                # Wait for the interval
                await asyncio.sleep(interval_minutes * 60)

                # Generate and send chat message
                await self._generate_and_send_chat()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in friendly chat scheduler: {e}", exc_info=True)
                # Wait a bit before retrying to avoid rapid failures
                await asyncio.sleep(60)

    async def _generate_and_send_chat(self):
        """Generate a friendly chat message and send it"""
        try:
            chat_settings = self.settings.get_friendly_chat_settings()
            data_window_minutes = chat_settings.get("data_window", 20)

            # Get recent activities
            activities = await self._get_recent_activities(data_window_minutes)

            if not activities:
                logger.debug("No recent activities found, skipping chat generation")
                return

            # Generate chat message using LLM
            chat_message = await self._generate_chat_message(activities)

            if not chat_message:
                logger.warning("Failed to generate chat message")
                return

            # Save to database
            chat_id = await self._save_chat_message(chat_message)

            # Send notifications based on settings
            await self._send_notifications(chat_message, chat_id, chat_settings)

            logger.info(
                f"✓ Friendly chat message generated and sent: {chat_message[:50]}..."
            )

        except Exception as e:
            logger.error(f"Error generating and sending chat: {e}", exc_info=True)

    async def _get_recent_activities(self, window_minutes: int) -> List[Dict[str, Any]]:
        """Get recent activities within the specified time window"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=window_minutes)

            # Query activities from database
            query = """
                SELECT id, description, start_time, end_time, source_events
                FROM activities
                WHERE start_time >= ?
                ORDER BY start_time DESC
                LIMIT 20
            """

            result = self.db.execute_query(query, (start_time.isoformat(),))

            activities = []
            for row in result:
                # Type hint: explicit str conversion for type checker
                activities.append(
                    {
                        "id": str(row[0]) if row[0] else "",
                        "description": str(row[1]) if row[1] else "",
                        "start_time": str(row[2]) if row[2] else "",
                        "end_time": str(row[3]) if row[3] else "",
                        "source_events": str(row[4]) if row[4] else "",
                    }
                )

            return activities

        except Exception as e:
            logger.error(f"Error getting recent activities: {e}", exc_info=True)
            return []

    async def _generate_chat_message(
        self, activities: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Generate a friendly chat message using LLM"""
        try:
            # Initialize LLM client if needed
            if self.llm_client is None:
                try:
                    self.llm_client = get_llm_client()
                except Exception as e:
                    logger.error(f"Failed to initialize LLM client: {e}")
                    return None

            # Build activity context
            activity_summary = self._build_activity_summary(activities)

            # Create prompt for LLM
            prompt = self._build_chat_prompt(activity_summary)

            # Build messages for chat completion
            messages = [{"role": "user", "content": prompt}]

            # Get config parameters from prompt manager
            config_params = self.prompt_manager.get_config_params("friendly_chat")

            # Call LLM client
            response = await self.llm_client.chat_completion(
                messages=messages,
                max_tokens=config_params.get("max_tokens", 150),
                temperature=config_params.get("temperature", 0.9),
            )

            if not response or not response.get("content"):
                logger.warning("LLM response is empty")
                return None

            raw_content = response["content"].strip()

            # Try to parse JSON and extract the message field
            chat_message = None
            try:
                parsed = parse_json_from_response(raw_content)
                if isinstance(parsed, dict) and parsed.get("message"):
                    chat_message = str(parsed["message"]).strip()
            except Exception as e:
                logger.debug(f"Failed to parse JSON friendly chat: {e}")

            # Fallback to raw content if JSON parsing failed
            if not chat_message:
                chat_message = raw_content

            # Record token usage to dashboard
            try:
                from core.dashboard.manager import get_dashboard_manager

                dashboard = get_dashboard_manager()
                dashboard.record_llm_request(
                    model=self.llm_client.model,
                    prompt_tokens=response.get("prompt_tokens", 0),
                    completion_tokens=response.get("completion_tokens", 0),
                    total_tokens=response.get("total_tokens", 0),
                    cost=response.get("cost", 0.0),
                    request_type="friendly_chat",
                )
            except Exception as e:
                logger.debug(f"Failed to record LLM usage: {e}")

            return chat_message

        except Exception as e:
            logger.error(f"Error generating chat message: {e}", exc_info=True)
            return None

    def _build_activity_summary(self, activities: List[Dict[str, Any]]) -> str:
        """Build a summary of recent activities"""
        if not activities:
            return "用户最近没有什么活动记录。"

        summary_parts = []
        for i, activity in enumerate(activities[:5], 1):  # Limit to top 5
            desc = activity.get("description", "未知活动")
            start_time = activity.get("start_time", "")

            # Parse time for better formatting
            try:
                dt = datetime.fromisoformat(start_time)
                time_str = dt.strftime("%H:%M")
                summary_parts.append(f"{i}. {time_str} - {desc}")
            except:
                summary_parts.append(f"{i}. {desc}")

        return "\n".join(summary_parts)

    def _build_chat_prompt(self, activity_summary: str) -> str:
        """Build the prompt for generating friendly chat"""
        # Get prompt from config file
        system_prompt = self.prompt_manager.get_prompt("friendly_chat", "system_prompt")
        user_prompt_template = self.prompt_manager.get_prompt(
            "friendly_chat", "user_prompt_template"
        )

        # Format user prompt with activity summary
        user_prompt = user_prompt_template.format(activity_summary=activity_summary)

        # Combine system and user prompts
        return f"{system_prompt}\n\n{user_prompt}"

    async def _save_chat_message(self, message: str) -> str:
        """Save chat message to database"""
        try:
            chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            timestamp = datetime.now().isoformat()

            insert_query = """
                INSERT INTO friendly_chats (id, message, timestamp, created_at)
                VALUES (?, ?, ?, ?)
            """

            self.db.execute_update(
                insert_query, (chat_id, message, timestamp, timestamp)
            )

            return chat_id

        except Exception as e:
            logger.error(f"Error saving chat message: {e}", exc_info=True)
            return ""

    async def _send_notifications(
        self, message: str, chat_id: str, settings: Dict[str, Any]
    ):
        """Send notifications based on settings"""
        try:
            payload = {
                "id": chat_id,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }

            # Send to Live2D if enabled (also check if Live2D itself is enabled)
            if settings.get("enable_live2d_display", True):
                # Check if Live2D is enabled in system settings
                live2d_settings = self.settings.get_live2d_settings()
                if live2d_settings.get("enabled", False):
                    _emit("friendly-chat-live2d", payload)
                    logger.debug("Sent chat to Live2D")
                else:
                    logger.debug(
                        "Live2D display requested but Live2D is not enabled, skipping"
                    )

            # Send system notification if enabled
            if settings.get("enable_system_notification", True):
                _emit("friendly-chat-notification", payload)
                logger.debug("Sent system notification")

        except Exception as e:
            logger.error(f"Error sending notifications: {e}", exc_info=True)

    async def get_chat_history(
        self, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get chat message history"""
        try:
            query = """
                SELECT id, message, timestamp, created_at
                FROM friendly_chats
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """

            result = self.db.execute_query(query, (limit, offset))

            history = []
            for row in result:
                history.append(
                    {
                        "id": row[0],
                        "message": row[1],
                        "timestamp": row[2],
                        "created_at": row[3],
                    }
                )

            return history

        except Exception as e:
            logger.error(f"Error getting chat history: {e}", exc_info=True)
            return []

    async def trigger_immediate_chat(self) -> Optional[str]:
        """Manually trigger a chat message generation"""
        try:
            chat_settings = self.settings.get_friendly_chat_settings()
            data_window_minutes = chat_settings.get("data_window", 20)

            # Get recent activities
            activities = await self._get_recent_activities(data_window_minutes)

            if not activities:
                logger.warning("No recent activities found for immediate chat")
                return None

            # Generate chat message
            chat_message = await self._generate_chat_message(activities)

            if chat_message:
                # Save and send
                chat_id = await self._save_chat_message(chat_message)
                await self._send_notifications(chat_message, chat_id, chat_settings)

            return chat_message

        except Exception as e:
            logger.error(f"Error triggering immediate chat: {e}", exc_info=True)
            return None


# Global service instance
_friendly_chat_service: Optional[FriendlyChatService] = None


def get_friendly_chat_service() -> FriendlyChatService:
    """Get global friendly chat service instance"""
    global _friendly_chat_service
    if _friendly_chat_service is None:
        _friendly_chat_service = FriendlyChatService()
    return _friendly_chat_service


async def init_friendly_chat_service() -> FriendlyChatService:
    """Initialize and start friendly chat service if enabled"""
    service = get_friendly_chat_service()

    # Ensure database table exists
    _ensure_chat_table()

    # Start if enabled
    settings = get_settings()
    chat_settings = settings.get_friendly_chat_settings()

    if chat_settings.get("enabled", False):
        await service.start()

    return service


def _ensure_chat_table():
    """Ensure the friendly_chats table exists in database"""
    try:
        db = get_db()
        create_table_query = """
            CREATE TABLE IF NOT EXISTS friendly_chats (
                id TEXT PRIMARY KEY,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """
        db.execute_update(create_table_query, ())
        logger.debug("✓ Friendly chats table ensured")
    except Exception as e:
        logger.error(f"Error creating friendly_chats table: {e}", exc_info=True)
