"""
数据持久化接口（新架构）
处理 events, knowledge, todos, activities, diaries 的数据库存储
"""

import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from pathlib import Path
from core.logger import get_logger

logger = get_logger(__name__)

# 导入数据库模块
try:
    from db.init import get_db_connection
except ImportError:
    # 备用路径
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from db.init import get_db_connection


class ProcessingPersistence:
    """处理数据持久化器（新架构）"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化持久化器

        Args:
            db_path: 数据库文件路径（可选）
        """
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return get_db_connection(self.db_path)

    # ============ Event 相关方法 ============

    async def save_event(self, event: Dict[str, Any]) -> bool:
        """
        保存event到数据库

        Args:
            event: event数据字典，包含 id, title, description, keywords, timestamp

        Returns:
            是否保存成功
        """
        try:
            query = """
                INSERT INTO events (id, title, description, keywords, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            keywords_json = json.dumps(event.get("keywords", []), ensure_ascii=False)
            timestamp = event.get("timestamp")
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()

            params = (
                event["id"],
                event["title"],
                event["description"],
                keywords_json,
                timestamp,
                datetime.now().isoformat()
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Event已保存: {event['id']}")
            return True

        except Exception as e:
            logger.error(f"保存event失败: {e}")
            return False

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取最近的events

        Args:
            limit: 返回数量

        Returns:
            event列表
        """
        try:
            query = """
                SELECT id, title, description, keywords, timestamp, created_at
                FROM events
                ORDER BY timestamp DESC
                LIMIT ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (limit,))
                rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                    "timestamp": row["timestamp"],
                    "created_at": row["created_at"]
                })

            return events

        except Exception as e:
            logger.error(f"获取最近events失败: {e}")
            return []

    async def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """按类型获取事件（新架构暂不区分类型，返回最近事件）"""
        logger.warning("新架构事件未存储类型信息，忽略 event_type=%s", event_type)
        return await self.get_recent_events(limit)

    async def get_events_in_timeframe(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """获取指定时间范围内的事件"""
        try:
            query = """
                SELECT id, title, description, keywords, timestamp, created_at
                FROM events
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (start_time.isoformat(), end_time.isoformat()))
                rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                    "timestamp": datetime.fromisoformat(row["timestamp"]),
                    "created_at": row["created_at"]
                })

            return events

        except Exception as e:
            logger.error(f"按时间范围获取events失败: {e}")
            return []

    async def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取事件详情"""
        try:
            query = """
                SELECT id, title, description, keywords, timestamp, created_at
                FROM events
                WHERE id = ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (event_id,))
                row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                "timestamp": row["timestamp"],
                "created_at": row["created_at"]
            }

        except Exception as e:
            logger.error(f"根据ID获取event失败: {e}")
            return None

    async def get_unsummarized_events(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        获取未被聚合成activity的events

        Args:
            since: 起始时间（可选）

        Returns:
            event列表
        """
        try:
            # 简化版本：获取最近未在activities中被引用的events
            # 实际应该检查 activities.source_event_ids 是否包含该event
            if since:
                query = """
                    SELECT id, title, description, keywords, timestamp, created_at
                    FROM events
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """
                params = (since.isoformat(),)
            else:
                # 获取最近1小时的events
                query = """
                    SELECT id, title, description, keywords, timestamp, created_at
                    FROM events
                    WHERE timestamp >= datetime('now', '-1 hour')
                    ORDER BY timestamp ASC
                """
                params = ()

            with self._get_conn() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                # 获取所有已聚合的 event ids
                cursor = conn.execute("""
                    SELECT source_event_ids
                    FROM activities
                    WHERE deleted = 0
                """)
                aggregated_rows = cursor.fetchall()

            events = []
            aggregated_ids = set()

            for row in aggregated_rows:
                source_ids = row["source_event_ids"]
                if not source_ids:
                    continue
                try:
                    for event_id in json.loads(source_ids):
                        aggregated_ids.add(event_id)
                except (TypeError, json.JSONDecodeError):
                    continue

            for row in rows:
                if row["id"] in aggregated_ids:
                    continue

                events.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                    "timestamp": datetime.fromisoformat(row["timestamp"]),
                    "created_at": row["created_at"]
                })

            return events

        except Exception as e:
            logger.error(f"获取未总结events失败: {e}")
            return []

    # ============ Knowledge 相关方法 ============

    async def save_knowledge(self, knowledge: Dict[str, Any]) -> bool:
        """
        保存knowledge到数据库

        Args:
            knowledge: knowledge数据字典

        Returns:
            是否保存成功
        """
        try:
            query = """
                INSERT INTO knowledge (id, title, description, keywords, created_at, deleted)
                VALUES (?, ?, ?, ?, ?, 0)
            """
            keywords_json = json.dumps(knowledge.get("keywords", []), ensure_ascii=False)
            created_at = knowledge.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                knowledge["id"],
                knowledge["title"],
                knowledge["description"],
                keywords_json,
                created_at or datetime.now().isoformat()
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Knowledge已保存: {knowledge['id']}")
            return True

        except Exception as e:
            logger.error(f"保存knowledge失败: {e}")
            return False

    async def get_unmerged_knowledge(self) -> List[Dict[str, Any]]:
        """
        获取未被合并的knowledge

        Returns:
            knowledge列表
        """
        try:
            # 获取不在combined_knowledge.merged_from_ids中的knowledge
            query = """
                SELECT k.id, k.title, k.description, k.keywords, k.created_at
                FROM knowledge k
                WHERE k.deleted = 0
                ORDER BY k.created_at ASC
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()

                # 获取已合并的 knowledge ids
                cursor = conn.execute("""
                    SELECT merged_from_ids
                    FROM combined_knowledge
                    WHERE deleted = 0
                """)
                merged_rows = cursor.fetchall()

            knowledge_list = []
            merged_ids = set()

            for row in merged_rows:
                merged = row["merged_from_ids"]
                if not merged:
                    continue
                try:
                    for item_id in json.loads(merged):
                        merged_ids.add(item_id)
                except (TypeError, json.JSONDecodeError):
                    continue

            for row in rows:
                if row["id"] in merged_ids:
                    continue

                knowledge_list.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                    "created_at": row["created_at"]
                })

            return knowledge_list

        except Exception as e:
            logger.error(f"获取未合并knowledge失败: {e}")
            return []

    async def save_combined_knowledge(self, combined: Dict[str, Any]) -> bool:
        """
        保存combined_knowledge到数据库

        Args:
            combined: combined_knowledge数据字典

        Returns:
            是否保存成功
        """
        try:
            query = """
                INSERT INTO combined_knowledge (id, title, description, keywords, merged_from_ids, created_at, deleted)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """
            keywords_json = json.dumps(combined.get("keywords", []), ensure_ascii=False)
            merged_from_ids_json = json.dumps(combined.get("merged_from_ids", []), ensure_ascii=False)
            created_at = combined.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                combined["id"],
                combined["title"],
                combined["description"],
                keywords_json,
                merged_from_ids_json,
                created_at or datetime.now().isoformat()
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"CombinedKnowledge已保存: {combined['id']}")
            return True

        except Exception as e:
            logger.error(f"保存combined_knowledge失败: {e}")
            return False

    async def get_knowledge_list(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        获取knowledge列表（优先返回combined）

        Args:
            include_deleted: 是否包含已删除的

        Returns:
            knowledge列表
        """
        try:
            # 先获取combined_knowledge
            if include_deleted:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, deleted
                    FROM combined_knowledge
                    ORDER BY created_at DESC
                """
            else:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, deleted
                    FROM combined_knowledge
                    WHERE deleted = 0
                    ORDER BY created_at DESC
                """

            with self._get_conn() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()

            knowledge_list = []
            for row in rows:
                knowledge_list.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                    "merged_from_ids": json.loads(row["merged_from_ids"]) if row["merged_from_ids"] else [],
                    "created_at": row["created_at"],
                    "deleted": bool(row["deleted"]),
                    "type": "combined"
                })

            # 如果没有combined_knowledge，返回原始knowledge
            if not knowledge_list:
                if include_deleted:
                    query = """
                        SELECT id, title, description, keywords, created_at, deleted
                        FROM knowledge
                        ORDER BY created_at DESC
                    """
                else:
                    query = """
                        SELECT id, title, description, keywords, created_at, deleted
                        FROM knowledge
                        WHERE deleted = 0
                        ORDER BY created_at DESC
                    """

                with self._get_conn() as conn:
                    cursor = conn.execute(query)
                    rows = cursor.fetchall()

                for row in rows:
                    knowledge_list.append({
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                        "created_at": row["created_at"],
                        "deleted": bool(row["deleted"]),
                        "type": "original"
                    })

            return knowledge_list

        except Exception as e:
            logger.error(f"获取knowledge列表失败: {e}")
            return []

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """
        删除knowledge（软删除）

        Args:
            knowledge_id: knowledge ID

        Returns:
            是否成功
        """
        try:
            # 先尝试从combined_knowledge中删除
            query1 = "UPDATE combined_knowledge SET deleted = 1 WHERE id = ?"
            query2 = "UPDATE knowledge SET deleted = 1 WHERE id = ?"

            with self._get_conn() as conn:
                cursor = conn.execute(query1, (knowledge_id,))
                if cursor.rowcount == 0:
                    # 如果combined中没有，从原始knowledge中删除
                    conn.execute(query2, (knowledge_id,))
                conn.commit()

            logger.debug(f"Knowledge已删除: {knowledge_id}")
            return True

        except Exception as e:
            logger.error(f"删除knowledge失败: {e}")
            return False

    # ============ Todo 相关方法 ============

    async def save_todo(self, todo: Dict[str, Any]) -> bool:
        """
        保存todo到数据库

        Args:
            todo: todo数据字典

        Returns:
            是否保存成功
        """
        try:
            query = """
                INSERT INTO todos (id, title, description, keywords, created_at, completed, deleted)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """
            keywords_json = json.dumps(todo.get("keywords", []), ensure_ascii=False)
            created_at = todo.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                todo["id"],
                todo["title"],
                todo["description"],
                keywords_json,
                created_at or datetime.now().isoformat(),
                int(todo.get("completed", False))
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Todo已保存: {todo['id']}")
            return True

        except Exception as e:
            logger.error(f"保存todo失败: {e}")
            return False

    async def get_unmerged_todos(self) -> List[Dict[str, Any]]:
        """
        获取未被合并的todos

        Returns:
            todo列表
        """
        try:
            query = """
                SELECT t.id, t.title, t.description, t.keywords, t.created_at, t.completed
                FROM todos t
                WHERE t.deleted = 0
                ORDER BY t.created_at ASC
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()

                # 获取已合并的 todos ids
                cursor = conn.execute("""
                    SELECT merged_from_ids
                    FROM combined_todos
                    WHERE deleted = 0
                """)
                merged_rows = cursor.fetchall()

            todo_list = []
            merged_ids = set()

            for row in merged_rows:
                merged = row["merged_from_ids"]
                if not merged:
                    continue
                try:
                    for item_id in json.loads(merged):
                        merged_ids.add(item_id)
                except (TypeError, json.JSONDecodeError):
                    continue

            for row in rows:
                if row["id"] in merged_ids:
                    continue

                todo_list.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                    "created_at": row["created_at"],
                    "completed": bool(row["completed"])
                })

            return todo_list

        except Exception as e:
            logger.error(f"获取未合并todos失败: {e}")
            return []

    async def save_combined_todo(self, combined: Dict[str, Any]) -> bool:
        """
        保存combined_todo到数据库

        Args:
            combined: combined_todo数据字典

        Returns:
            是否保存成功
        """
        try:
            query = """
                INSERT INTO combined_todos (id, title, description, keywords, merged_from_ids, created_at, completed, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """
            keywords_json = json.dumps(combined.get("keywords", []), ensure_ascii=False)
            merged_from_ids_json = json.dumps(combined.get("merged_from_ids", []), ensure_ascii=False)
            created_at = combined.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                combined["id"],
                combined["title"],
                combined["description"],
                keywords_json,
                merged_from_ids_json,
                created_at or datetime.now().isoformat(),
                int(combined.get("completed", False))
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"CombinedTodo已保存: {combined['id']}")
            return True

        except Exception as e:
            logger.error(f"保存combined_todo失败: {e}")
            return False

    async def get_todo_list(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        """
        获取todo列表（优先返回combined）

        Args:
            include_completed: 是否包含已完成的

        Returns:
            todo列表
        """
        try:
            # 先获取combined_todos
            if include_completed:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, completed, deleted
                    FROM combined_todos
                    WHERE deleted = 0
                    ORDER BY completed ASC, created_at DESC
                """
            else:
                query = """
                    SELECT id, title, description, keywords, merged_from_ids, created_at, completed, deleted
                    FROM combined_todos
                    WHERE deleted = 0 AND completed = 0
                    ORDER BY created_at DESC
                """

            with self._get_conn() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()

            todo_list = []
            for row in rows:
                todo_list.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                    "merged_from_ids": json.loads(row["merged_from_ids"]) if row["merged_from_ids"] else [],
                    "created_at": row["created_at"],
                    "completed": bool(row["completed"]),
                    "deleted": bool(row["deleted"]),
                    "type": "combined"
                })

            # 如果没有combined_todos，返回原始todos
            if not todo_list:
                if include_completed:
                    query = """
                        SELECT id, title, description, keywords, created_at, completed, deleted
                        FROM todos
                        WHERE deleted = 0
                        ORDER BY completed ASC, created_at DESC
                    """
                else:
                    query = """
                        SELECT id, title, description, keywords, created_at, completed, deleted
                        FROM todos
                        WHERE deleted = 0 AND completed = 0
                        ORDER BY created_at DESC
                    """

                with self._get_conn() as conn:
                    cursor = conn.execute(query)
                    rows = cursor.fetchall()

                for row in rows:
                    todo_list.append({
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                        "created_at": row["created_at"],
                        "completed": bool(row["completed"]),
                        "deleted": bool(row["deleted"]),
                        "type": "original"
                    })

            return todo_list

        except Exception as e:
            logger.error(f"获取todo列表失败: {e}")
            return []

    async def delete_todo(self, todo_id: str) -> bool:
        """
        删除todo（软删除）

        Args:
            todo_id: todo ID

        Returns:
            是否成功
        """
        try:
            # 先尝试从combined_todos中删除
            query1 = "UPDATE combined_todos SET deleted = 1 WHERE id = ?"
            query2 = "UPDATE todos SET deleted = 1 WHERE id = ?"

            with self._get_conn() as conn:
                cursor = conn.execute(query1, (todo_id,))
                if cursor.rowcount == 0:
                    # 如果combined中没有，从原始todos中删除
                    conn.execute(query2, (todo_id,))
                conn.commit()

            logger.debug(f"Todo已删除: {todo_id}")
            return True

        except Exception as e:
            logger.error(f"删除todo失败: {e}")
            return False

    # ============ Activity 相关方法 ============

    async def save_activity(self, activity: Dict[str, Any]) -> bool:
        """
        保存activity到数据库

        Args:
            activity: activity数据字典

        Returns:
            是否保存成功
        """
        try:
            query = """
                INSERT INTO activities (id, title, description, start_time, end_time, source_event_ids, created_at, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """
            source_event_ids_json = json.dumps(activity.get("source_event_ids", []), ensure_ascii=False)

            start_time = activity.get("start_time")
            if isinstance(start_time, datetime):
                start_time = start_time.isoformat()

            end_time = activity.get("end_time")
            if isinstance(end_time, datetime):
                end_time = end_time.isoformat()

            created_at = activity.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                activity["id"],
                activity["title"],
                activity["description"],
                start_time,
                end_time,
                source_event_ids_json,
                created_at or datetime.now().isoformat()
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Activity已保存: {activity['id']}")
            return True

        except Exception as e:
            logger.error(f"保存activity失败: {e}")
            return False

    async def get_recent_activities(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取最近的activities

        Args:
            limit: 返回数量
            offset: 偏移量（用于分页）

        Returns:
            activity列表
        """
        try:
            query = """
                SELECT id, title, description, start_time, end_time, source_event_ids, created_at
                FROM activities
                WHERE deleted = 0
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (limit, offset))
                rows = cursor.fetchall()

            activities = []
            for row in rows:
                activities.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "source_event_ids": json.loads(row["source_event_ids"]) if row["source_event_ids"] else [],
                    "created_at": row["created_at"]
                })

            return activities

        except Exception as e:
            logger.error(f"获取最近activities失败: {e}")
            return []

    async def get_activity_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取活动详情"""
        try:
            query = """
                SELECT id, title, description, start_time, end_time, source_event_ids, created_at
                FROM activities
                WHERE id = ? AND deleted = 0
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (activity_id,))
                row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "source_event_ids": json.loads(row["source_event_ids"]) if row["source_event_ids"] else [],
                "created_at": row["created_at"]
            }

        except Exception as e:
            logger.error(f"根据ID获取activity失败: {e}")
            return None

    async def get_events_by_ids(self, event_ids: List[str]) -> List[Dict[str, Any]]:
        """批量获取事件详情"""
        if not event_ids:
            return []

        try:
            placeholders = ",".join(["?"] * len(event_ids))
            query = f"""
                SELECT id, title, description, keywords, timestamp, created_at
                FROM events
                WHERE id IN ({placeholders})
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, tuple(event_ids))
                rows = cursor.fetchall()

            events: List[Dict[str, Any]] = []
            for row in rows:
                events.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                    "timestamp": row["timestamp"],
                    "created_at": row["created_at"]
                })

            return events

        except Exception as e:
            logger.error(f"批量获取events失败: {e}")
            return []

    async def delete_activity(self, activity_id: str) -> bool:
        """软删除指定的活动"""
        try:
            query = "UPDATE activities SET deleted = 1 WHERE id = ?"
            with self._get_conn() as conn:
                cursor = conn.execute(query, (activity_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除activity失败: {e}")
            return False

    async def get_activities_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        获取指定日期的所有activities

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)

        Returns:
            activity列表
        """
        try:
            # 解析日期
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())

            query = """
                SELECT id, title, description, start_time, end_time, source_event_ids, created_at
                FROM activities
                WHERE deleted = 0
                  AND start_time >= ?
                  AND start_time <= ?
                ORDER BY start_time ASC
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (start_datetime.isoformat(), end_datetime.isoformat()))
                rows = cursor.fetchall()

            activities = []
            for row in rows:
                activities.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "source_event_ids": json.loads(row["source_event_ids"]) if row["source_event_ids"] else [],
                    "created_at": row["created_at"]
                })

            return activities

        except Exception as e:
            logger.error(f"获取指定日期activities失败: {e}")
            return []

    # ============ Diary 相关方法 ============

    async def save_diary(self, diary: Dict[str, Any]) -> bool:
        """
        保存diary到数据库

        Args:
            diary: diary数据字典

        Returns:
            是否保存成功
        """
        try:
            query = """
                INSERT OR REPLACE INTO diaries (id, date, content, source_activity_ids, created_at, deleted)
                VALUES (?, ?, ?, ?, ?, 0)
            """
            source_activity_ids_json = json.dumps(diary.get("source_activity_ids", []), ensure_ascii=False)
            created_at = diary.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            params = (
                diary["id"],
                diary["date"],
                diary["content"],
                source_activity_ids_json,
                created_at or datetime.now().isoformat()
            )

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()

            logger.debug(f"Diary已保存: {diary['date']}")
            return True

        except Exception as e:
            logger.error(f"保存diary失败: {e}")
            return False

    async def get_diary_by_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        获取指定日期的diary

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)

        Returns:
            diary数据或None
        """
        try:
            query = """
                SELECT id, date, content, source_activity_ids, created_at
                FROM diaries
                WHERE date = ? AND deleted = 0
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (date_str,))
                row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "date": row["date"],
                    "content": row["content"],
                    "source_activity_ids": json.loads(row["source_activity_ids"]) if row["source_activity_ids"] else [],
                    "created_at": row["created_at"]
                }
            return None

        except Exception as e:
            logger.error(f"获取diary失败: {e}")
            return None

    async def delete_diary(self, diary_id: str) -> bool:
        """
        删除diary（软删除）

        Args:
            diary_id: diary ID

        Returns:
            是否成功
        """
        try:
            query = "UPDATE diaries SET deleted = 1 WHERE id = ?"

            with self._get_conn() as conn:
                conn.execute(query, (diary_id,))
                conn.commit()

            logger.debug(f"Diary已删除: {diary_id}")
            return True

        except Exception as e:
            logger.error(f"删除diary失败: {e}")
            return False

    async def delete_old_data(self, days: int = 30) -> Dict[str, Any]:
        """清理指定天数之前的数据"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            cutoff_iso = cutoff.isoformat()

            deleted_counts = {
                "events": 0,
                "activities": 0,
                "knowledge": 0,
                "todos": 0,
                "combinedKnowledge": 0,
                "combinedTodos": 0,
                "diaries": 0
            }

            with self._get_conn() as conn:
                cursor = conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff_iso,))
                deleted_counts["events"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE activities SET deleted = 1 WHERE deleted = 0 AND start_time < ?",
                    (cutoff_iso,)
                )
                deleted_counts["activities"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE knowledge SET deleted = 1 WHERE deleted = 0 AND created_at < ?",
                    (cutoff_iso,)
                )
                deleted_counts["knowledge"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE todos SET deleted = 1 WHERE deleted = 0 AND created_at < ?",
                    (cutoff_iso,)
                )
                deleted_counts["todos"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE combined_knowledge SET deleted = 1 WHERE deleted = 0 AND created_at < ?",
                    (cutoff_iso,)
                )
                deleted_counts["combinedKnowledge"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE combined_todos SET deleted = 1 WHERE deleted = 0 AND created_at < ?",
                    (cutoff_iso,)
                )
                deleted_counts["combinedTodos"] = cursor.rowcount

                cursor = conn.execute(
                    "UPDATE diaries SET deleted = 1 WHERE deleted = 0 AND date < ?",
                    (cutoff.strftime("%Y-%m-%d"),)
                )
                deleted_counts["diaries"] = cursor.rowcount

                conn.commit()

            return deleted_counts

        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return {"error": str(e)}  # type: ignore[return-value]

    def get_stats(self) -> Dict[str, Any]:
        """获取持久化层统计信息"""
        try:
            stats = {}
            with self._get_conn() as conn:
                for table in [
                    "events",
                    "activities",
                    "knowledge",
                    "todos",
                    "combined_knowledge",
                    "combined_todos",
                    "diaries"
                ]:
                    cursor = conn.execute(f"SELECT COUNT(1) AS count FROM {table} WHERE deleted = 0" if table in [
                        "activities",
                        "knowledge",
                        "todos",
                        "combined_knowledge",
                        "combined_todos",
                        "diaries"
                    ] else f"SELECT COUNT(1) AS count FROM {table}")
                    row = cursor.fetchone()
                    stats[table] = row["count"] if row else 0

                db_path = self.db_path or Path(__file__).parent.parent / "db" / "rewind.db"
                try:
                    size_bytes = Path(db_path).stat().st_size
                except OSError:
                    size_bytes = 0

            stats["databasePath"] = str(db_path)
            stats["databaseSize"] = size_bytes
            return stats

        except Exception as e:
            logger.error(f"获取持久化统计失败: {e}")
            return {"error": str(e)}

    async def get_diary_list(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最新的diary列表

        Args:
            limit: 返回数量

        Returns:
            diary列表
        """
        try:
            query = """
                SELECT id, date, content, source_activity_ids, created_at
                FROM diaries
                WHERE deleted = 0
                ORDER BY date DESC
                LIMIT ?
            """

            with self._get_conn() as conn:
                cursor = conn.execute(query, (limit,))
                rows = cursor.fetchall()

            diaries = []
            for row in rows:
                diaries.append({
                    "id": row["id"],
                    "date": row["date"],
                    "content": row["content"],
                    "source_activity_ids": json.loads(row["source_activity_ids"]) if row["source_activity_ids"] else [],
                    "created_at": row["created_at"]
                })

            return diaries

        except Exception as e:
            logger.error(f"获取diary列表失败: {e}")
            return []
