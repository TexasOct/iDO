"""
SQLite 数据库封装
提供连接、查询、插入、更新等基础操作
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path
from core.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "rewind.db"):
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
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建 activities 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    source_events TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
            
            conn.commit()
            logger.info("数据库表创建完成")
    
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
            return cursor.lastrowid
    
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
    def insert_activity(self, activity_id: str, description: str, start_time: str, 
                       end_time: str, source_events: List[Dict[str, Any]]) -> int:
        """插入活动"""
        query = """
            INSERT INTO activities (id, description, start_time, end_time, source_events)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (activity_id, description, start_time, end_time, json.dumps(source_events))
        return self.execute_insert(query, params)
    
    def get_activities(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取活动"""
        query = """
            SELECT * FROM activities
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
        """
        return self.execute_query(query, (limit, offset))
    
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


# 全局数据库管理器实例
db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """获取数据库管理器实例"""
    global db_manager
    if db_manager is None:
        from config.loader import get_config
        config = get_config()
        db_url = config.get('database.url', 'sqlite:///./rewind.db')
        # 从 URL 中提取数据库路径
        if db_url.startswith('sqlite:///'):
            db_path = db_url[10:]  # 移除 'sqlite:///' 前缀
        else:
            db_path = 'rewind.db'
        db_manager = DatabaseManager(db_path)
    return db_manager
