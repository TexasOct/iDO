"""
SQLite 数据库封装
提供连接、查询、插入、更新等基础操作
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path
from core.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: Optional[str] = None):
        # 如果没有提供路径，使用统一的数据目录
        if db_path is None:
            from core.paths import get_db_path
            db_path = str(get_db_path())

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        # 确保数据库目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # 创建表
        self._create_tables()
        logger.info(f"数据库初始化完成: {self.db_path}")

    def _create_tables(self):
        """创建数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 创建 raw_records 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建 events 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    type TEXT,
                    summary TEXT,
                    source_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建 activities 表（包含版本号字段用于增量更新）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    source_events TEXT,
                    source_event_ids TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    deleted BOOLEAN DEFAULT 0
                )
            """)

            # 创建 tasks 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agent_type TEXT,
                    parameters TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建 settings 表（存储持久化配置）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建 conversations 表（对话）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    related_activity_ids TEXT,
                    metadata TEXT
                )
            """)

            # 创建 messages 表（消息）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)

            # 创建 llm_token_usage 表（LLM Token使用统计）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    request_type TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建 event_images 表（事件对应的截图哈希）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                    UNIQUE(event_id, hash)
                )
            """)

            # 创建 llm_models 表（模型配置）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    provider TEXT NOT NULL,
                    api_url TEXT NOT NULL,
                    model TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    input_token_price REAL NOT NULL DEFAULT 0.0,
                    output_token_price REAL NOT NULL DEFAULT 0.0,
                    currency TEXT DEFAULT 'USD',
                    is_active INTEGER DEFAULT 0,
                    last_test_status INTEGER DEFAULT 0,
                    last_tested_at TEXT,
                    last_test_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK(input_token_price >= 0),
                    CHECK(output_token_price >= 0)
                )
            """)

            # 创建索引优化查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                ON conversations(updated_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_images_event_id
                ON event_images(event_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_images_hash
                ON event_images(hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_usage_timestamp
                ON llm_token_usage(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_usage_model
                ON llm_token_usage(model)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_models_provider
                ON llm_models(provider)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_models_is_active
                ON llm_models(is_active)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_models_created_at
                ON llm_models(created_at DESC)
            """)

            conn.commit()
            # 检查表是否需要迁移（添加新字段）
            self._migrate_events_table(cursor, conn)
            self._migrate_activities_table(cursor, conn)
            self._migrate_llm_models_table(cursor, conn)
            logger.info("数据库表创建完成")

    def _migrate_events_table(self, cursor, conn):
        """迁移 events 表：添加 title, description, keywords, timestamp 列以兼容新架构，并修改 NOT NULL 约束"""
        try:
            cursor.execute("PRAGMA table_info(events)")
            columns = {row[1]: row for row in cursor.fetchall()}

            # 检查是否需要修改 NOT NULL 约束
            needs_constraint_fix = False
            for col_name in ['start_time', 'end_time', 'type', 'summary', 'source_data']:
                if col_name in columns:
                    # columns[col_name][3] 是 notnull 标记 (1 = NOT NULL, 0 = NULL)
                    if columns[col_name][3] == 1:  # 如果是 NOT NULL
                        needs_constraint_fix = True
                        break

            # 如果需要修改约束，重建表
            if needs_constraint_fix:
                logger.info("检测到 events 表需要修改 NOT NULL 约束，正在重建表...")
                # 创建临时表
                cursor.execute("""
                    CREATE TABLE events_new (
                        id TEXT PRIMARY KEY,
                        start_time TEXT,
                        end_time TEXT,
                        type TEXT,
                        summary TEXT,
                        source_data TEXT,
                        title TEXT DEFAULT '',
                        description TEXT DEFAULT '',
                        keywords TEXT,
                        timestamp TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 迁移数据
                cursor.execute("""
                    INSERT INTO events_new (
                        id, start_time, end_time, type, summary, source_data,
                        title, description, keywords, timestamp, created_at
                    )
                    SELECT
                        id, start_time, end_time, type, summary, source_data,
                        COALESCE(title, SUBSTR(COALESCE(summary, ''), 1, 100)),
                        COALESCE(description, COALESCE(summary, '')),
                        keywords, timestamp, created_at
                    FROM events
                """)

                # 删除旧表
                cursor.execute("DROP TABLE events")

                # 重命名新表
                cursor.execute("ALTER TABLE events_new RENAME TO events")

                # 重建索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON events(timestamp DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_events_created
                    ON events(created_at DESC)
                """)

                conn.commit()
                logger.info("已修改 events 表的 NOT NULL 约束")
            else:
                # 仅添加缺失的列
                if 'title' not in columns:
                    cursor.execute("""
                        ALTER TABLE events
                        ADD COLUMN title TEXT DEFAULT ''
                    """)
                    cursor.execute("""
                        UPDATE events
                        SET title = SUBSTR(COALESCE(summary, ''), 1, 100)
                        WHERE title = '' OR title IS NULL
                    """)
                    conn.commit()
                    logger.info("已为 events 表添加 title 列")

                if 'description' not in columns:
                    cursor.execute("""
                        ALTER TABLE events
                        ADD COLUMN description TEXT DEFAULT ''
                    """)
                    cursor.execute("""
                        UPDATE events
                        SET description = COALESCE(summary, '')
                        WHERE description = '' OR description IS NULL
                    """)
                    conn.commit()
                    logger.info("已为 events 表添加 description 列")

                if 'keywords' not in columns:
                    cursor.execute("""
                        ALTER TABLE events
                        ADD COLUMN keywords TEXT DEFAULT NULL
                    """)
                    conn.commit()
                    logger.info("已为 events 表添加 keywords 列")

                if 'timestamp' not in columns:
                    cursor.execute("""
                        ALTER TABLE events
                        ADD COLUMN timestamp TEXT DEFAULT NULL
                    """)
                    cursor.execute("""
                        UPDATE events
                        SET timestamp = start_time
                        WHERE timestamp IS NULL AND start_time IS NOT NULL
                    """)
                    conn.commit()
                    logger.info("已为 events 表添加 timestamp 列")
        except Exception as e:
            logger.warning(f"迁移 events 表时出错（可能列已存在）: {e}")

    def _migrate_activities_table(self, cursor, conn):
        """迁移 activities 表：修复 NOT NULL 约束，并添加缺失列"""
        try:
            # 检查列是否存在和约束
            cursor.execute("PRAGMA table_info(activities)")
            columns = {row[1]: row for row in cursor.fetchall()}

            # 检查是否需要修改 NOT NULL 约束
            needs_constraint_fix = False
            for col_name in ['source_events']:
                if col_name in columns:
                    # columns[col_name][3] 是 notnull 标记 (1 = NOT NULL, 0 = NULL)
                    if columns[col_name][3] == 1:  # 如果是 NOT NULL
                        needs_constraint_fix = True
                        break

            # 如果需要修改约束，重建表
            if needs_constraint_fix:
                logger.info("检测到 activities 表需要修改 NOT NULL 约束，正在重建表...")
                # 创建临时表（含新增的列）
                cursor.execute("""
                    CREATE TABLE activities_new (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        source_events TEXT,
                        version INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        deleted BOOLEAN DEFAULT 0,
                        source_event_ids TEXT
                    )
                """)

                # 迁移数据
                cursor.execute("""
                    INSERT INTO activities_new (
                        id, title, description, start_time, end_time, source_events,
                        version, created_at, deleted, source_event_ids
                    )
                    SELECT
                        id, COALESCE(title, SUBSTR(description, 1, 50)), description,
                        start_time, end_time, source_events,
                        COALESCE(version, 1), created_at,
                        COALESCE(deleted, 0), source_event_ids
                    FROM activities
                """)

                # 删除旧表
                cursor.execute("DROP TABLE activities")

                # 重命名新表
                cursor.execute("ALTER TABLE activities_new RENAME TO activities")

                conn.commit()
                logger.info("已修改 activities 表的 NOT NULL 约束")
            else:
                # 仅添加缺失的列
                column_names = [row[1] for row in columns.values()]

            # 检查列是否存在
            cursor.execute("PRAGMA table_info(activities)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'version' not in columns:
                # 添加 version 列，新增记录默认版本为 1
                cursor.execute("""
                    ALTER TABLE activities
                    ADD COLUMN version INTEGER DEFAULT 1
                """)
                conn.commit()
                logger.info("已为 activities 表添加 version 列")

            if 'title' not in columns:
                # 添加 title 列，对于已有记录使用 description 的前50个字符作为默认值
                cursor.execute("""
                    ALTER TABLE activities
                    ADD COLUMN title TEXT DEFAULT ''
                """)
                # 为现有记录设置title（使用description的前50个字符）
                cursor.execute("""
                    UPDATE activities
                    SET title = SUBSTR(description, 1, 50)
                    WHERE title = '' OR title IS NULL
                """)
                conn.commit()
                logger.info("已为 activities 表添加 title 列")

            if 'deleted' not in columns:
                cursor.execute("""
                    ALTER TABLE activities
                    ADD COLUMN deleted BOOLEAN DEFAULT 0
                """)
                conn.commit()
                logger.info("已为 activities 表添加 deleted 列")

            if 'source_event_ids' not in columns:
                # 添加 source_event_ids 列（新架构使用此列名）
                # 注意：这与 source_events 列可能存在冗余，但为了兼容性暂时保留两者
                cursor.execute("""
                    ALTER TABLE activities
                    ADD COLUMN source_event_ids TEXT DEFAULT NULL
                """)
                # 为现有记录从 source_events 中提取 event IDs
                cursor.execute("""
                    UPDATE activities
                    SET source_event_ids = source_events
                    WHERE source_event_ids IS NULL AND source_events IS NOT NULL
                """)
                conn.commit()
                logger.info("已为 activities 表添加 source_event_ids 列")
        except Exception as e:
            logger.warning(f"迁移 activities 表时出错（可能列已存在）: {e}")

    def _migrate_llm_models_table(self, cursor, conn):
        """迁移 llm_models 表：添加测试状态相关字段"""
        try:
            cursor.execute("PRAGMA table_info(llm_models)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'last_test_status' not in columns:
                cursor.execute("ALTER TABLE llm_models ADD COLUMN last_test_status INTEGER DEFAULT 0")
            if 'last_tested_at' not in columns:
                cursor.execute("ALTER TABLE llm_models ADD COLUMN last_tested_at TEXT")
            if 'last_test_error' not in columns:
                cursor.execute("ALTER TABLE llm_models ADD COLUMN last_test_error TEXT")

            conn.commit()
        except Exception as e:
            logger.warning(f"迁移 llm_models 表时出错（可能字段已存在）: {e}")

    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_insert(self, query: str, params: Tuple = ()) -> int:
        """执行插入操作并返回插入的ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid or 0

    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """执行更新操作并返回影响的行数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def execute_delete(self, query: str, params: Tuple = ()) -> int:
        """执行删除操作并返回影响的行数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    # 原始记录相关方法
    def insert_raw_record(self, timestamp: str, event_type: str, data: Dict[str, Any]) -> int:
        """插入原始记录"""
        query = """
            INSERT INTO raw_records (timestamp, type, data)
            VALUES (?, ?, ?)
        """
        params = (timestamp, event_type, json.dumps(data))
        return self.execute_insert(query, params)

    def get_raw_records(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取原始记录"""
        query = """
            SELECT * FROM raw_records
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))

    # 事件相关方法
    def insert_event(self, event_id: str, start_time: str, end_time: str,
                    event_type: str, summary: str, source_data: List[Dict[str, Any]]) -> int:
        """插入事件"""
        query = """
            INSERT INTO events (id, start_time, end_time, type, summary, source_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (event_id, start_time, end_time, event_type, summary, json.dumps(source_data))
        return self.execute_insert(query, params)

    def get_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取事件"""
        query = """
            SELECT * FROM events
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))

    # 活动相关方法
    def insert_activity(self, activity_id: str, title: str, description: str, start_time: str,
                       end_time: str, source_events: List[Dict[str, Any]]) -> int:
        """插入活动"""
        query = """
            INSERT INTO activities (id, title, description, start_time, end_time, source_events)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (activity_id, title, description, start_time, end_time, json.dumps(source_events))
        return self.execute_insert(query, params)

    def delete_activity(self, activity_id: str) -> int:
        """删除指定活动"""
        query = """
            DELETE FROM activities
            WHERE id = ?
        """
        return self.execute_delete(query, (activity_id,))

    def get_activities(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取活动"""
        query = """
            SELECT * FROM activities
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))

    def get_max_activity_version(self) -> int:
        """获取 activities 表的最大版本号"""
        query = "SELECT MAX(version) as max_version FROM activities"
        results = self.execute_query(query)
        if results and results[0].get('max_version'):
            return int(results[0]['max_version'])
        return 0

    def get_activities_after_version(self, version: int, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指定版本号之后的活动（增量更新）"""
        query = """
            SELECT * FROM activities
            WHERE version > ?
            ORDER BY version DESC, start_time DESC
            LIMIT ?
        """
        return self.execute_query(query, (version, limit))

    def get_activity_count_by_date(self) -> List[Dict[str, Any]]:
        """获取每天的活动总数统计"""
        query = """
            SELECT
                DATE(start_time) as date,
                COUNT(*) as count
            FROM activities
            GROUP BY DATE(start_time)
            ORDER BY date DESC
        """
        return self.execute_query(query)

    # 任务相关方法
    def insert_task(self, task_id: str, title: str, description: str, status: str,
                   agent_type: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> int:
        """插入任务"""
        query = """
            INSERT INTO tasks (id, title, description, status, agent_type, parameters)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (task_id, title, description, status, agent_type, json.dumps(parameters or {}))
        return self.execute_insert(query, params)

    def update_task_status(self, task_id: str, status: str) -> int:
        """更新任务状态"""
        query = """
            UPDATE tasks
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        return self.execute_update(query, (status, task_id))

    def get_tasks(self, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取任务"""
        if status:
            query = """
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            return self.execute_query(query, (status, limit, offset))
        else:
            query = """
                SELECT * FROM tasks
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            return self.execute_query(query, (limit, offset))

    # 配置相关方法
    def set_setting(self, key: str, value: str, setting_type: str = "string", description: Optional[str] = None) -> int:
        """设置配置项"""
        query = """
            INSERT OR REPLACE INTO settings (key, value, type, description, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (key, value, setting_type, description)
        return self.execute_insert(query, params)

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取配置项"""
        query = "SELECT value FROM settings WHERE key = ?"
        results = self.execute_query(query, (key,))
        if results:
            return results[0]['value']
        return default

    def get_all_settings(self) -> Dict[str, Any]:
        """获取所有配置项"""
        query = "SELECT key, value, type FROM settings ORDER BY key"
        results = self.execute_query(query)
        settings = {}
        for row in results:
            key = row['key']
            value = row['value']
            setting_type = row['type']

            # 类型转换
            if setting_type == 'bool':
                settings[key] = value.lower() in ('true', '1', 'yes')
            elif setting_type == 'int':
                try:
                    settings[key] = int(value)
                except ValueError:
                    settings[key] = value
            else:
                settings[key] = value
        return settings

    def delete_setting(self, key: str) -> int:
        """删除配置项"""
        query = "DELETE FROM settings WHERE key = ?"
        return self.execute_delete(query, (key,))

    # 对话相关方法
    def insert_conversation(self, conversation_id: str, title: str,
                           related_activity_ids: Optional[List[str]] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> int:
        """插入对话"""
        query = """
            INSERT INTO conversations (id, title, related_activity_ids, metadata)
            VALUES (?, ?, ?, ?)
        """
        params = (
            conversation_id,
            title,
            json.dumps(related_activity_ids or []),
            json.dumps(metadata or {})
        )
        return self.execute_insert(query, params)

    def get_conversations(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取对话列表（按更新时间倒序）"""
        query = """
            SELECT * FROM conversations
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))

    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取对话"""
        query = "SELECT * FROM conversations WHERE id = ?"
        results = self.execute_query(query, (conversation_id,))
        return results[0] if results else None

    def update_conversation(self, conversation_id: str, title: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> int:
        """更新对话"""
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return 0

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(conversation_id)

        query = f"""
            UPDATE conversations
            SET {', '.join(updates)}
            WHERE id = ?
        """
        return self.execute_update(query, tuple(params))

    def delete_conversation(self, conversation_id: str) -> int:
        """删除对话（级联删除消息）"""
        query = "DELETE FROM conversations WHERE id = ?"
        return self.execute_delete(query, (conversation_id,))

    # 消息相关方法
    def insert_message(self, message_id: str, conversation_id: str, role: str,
                      content: str, timestamp: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> int:
        """插入消息"""
        query = """
            INSERT INTO messages (id, conversation_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            message_id,
            conversation_id,
            role,
            content,
            timestamp or datetime.now().isoformat(),
            json.dumps(metadata or {})
        )
        return self.execute_insert(query, params)

    def get_messages(self, conversation_id: str, limit: int = 100,
                    offset: int = 0) -> List[Dict[str, Any]]:
        """获取对话的消息列表（按时间正序）"""
        query = """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (conversation_id, limit, offset))

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取消息"""
        query = "SELECT * FROM messages WHERE id = ?"
        results = self.execute_query(query, (message_id,))
        return results[0] if results else None

    def delete_message(self, message_id: str) -> int:
        """删除消息"""
        query = "DELETE FROM messages WHERE id = ?"
        return self.execute_delete(query, (message_id,))

    def get_message_count(self, conversation_id: str) -> int:
        """获取对话的消息数量"""
        query = "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?"
        results = self.execute_query(query, (conversation_id,))
        return results[0]['count'] if results else 0

    # LLM 模型管理相关方法
    def get_active_llm_model(self) -> Optional[Dict[str, Any]]:
        """获取当前激活的 LLM 模型配置"""
        query = """
            SELECT
                id,
                name,
                provider,
                api_url,
                model,
                api_key,
                input_token_price,
                output_token_price,
                currency,
                last_test_status,
                last_tested_at,
                last_test_error,
                created_at,
                updated_at
            FROM llm_models
            WHERE is_active = 1
            LIMIT 1
        """
        results = self.execute_query(query)
        return results[0] if results else None

    def get_llm_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取模型配置（包含密钥和测试状态）"""
        query = """
            SELECT
                id,
                name,
                provider,
                api_url,
                model,
                api_key,
                input_token_price,
                output_token_price,
                currency,
                is_active,
                last_test_status,
                last_tested_at,
                last_test_error,
                created_at,
                updated_at
            FROM llm_models
            WHERE id = ?
            LIMIT 1
        """
        results = self.execute_query(query, (model_id,))
        return results[0] if results else None

    def update_model_test_result(self, model_id: str, success: bool, error: Optional[str] = None) -> None:
        """更新模型测试结果"""
        now = datetime.now().isoformat()
        query = """
            UPDATE llm_models
            SET
                last_test_status = ?,
                last_tested_at = ?,
                last_test_error = ?,
                updated_at = ?
            WHERE id = ?
        """
        self.execute_update(query, (1 if success else 0, now, error, now, model_id))


# 全局数据库管理器实例
db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """获取数据库管理器实例

    从 config.toml 中的 database.path 读取数据库路径，
    如果未配置则使用默认路径 ~/.config/rewind/rewind.db
    """
    global db_manager
    if db_manager is None:
        from config.loader import get_config
        from core.paths import get_db_path

        config = get_config()

        # 从 config.toml 中读取数据库路径
        configured_path = config.get('database.path', '')

        # 如果配置了路径且不为空，使用配置的路径；否则使用默认路径
        if configured_path and configured_path.strip():
            db_path = configured_path
        else:
            db_path = str(get_db_path())

        db_manager = DatabaseManager(db_path)
        logger.info(f"✓ 数据库管理器初始化，路径: {db_path}")

    return db_manager


def switch_database(new_db_path: str) -> bool:
    """切换数据库到新路径（用于运行时修改数据库位置）

    Args:
        new_db_path: 新的数据库路径

    Returns:
        True if switch successful, False otherwise
    """
    global db_manager

    if db_manager is None:
        logger.error("数据库管理器未初始化")
        return False

    try:
        # 检查新路径是否相同
        if Path(db_manager.db_path).resolve() == Path(new_db_path).resolve():
            logger.info(f"新路径与当前路径相同，无需切换: {new_db_path}")
            return True

        # 关闭当前连接（DatabaseManager 使用上下文管理器，无需手动关闭）
        logger.info(f"关闭当前数据库连接: {db_manager.db_path}")
        # 注意：DatabaseManager 使用上下文管理器模式，连接会在使用后自动关闭

        # 创建新路径的目录
        Path(new_db_path).parent.mkdir(parents=True, exist_ok=True)

        # 创建新的数据库管理器
        db_manager = DatabaseManager(new_db_path)
        logger.info(f"✓ 数据库已切换到: {new_db_path}")
        return True

    except Exception as e:
        logger.error(f"切换数据库失败: {e}", exc_info=True)
        return False
