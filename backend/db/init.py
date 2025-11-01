"""
数据库初始化和连接管理
"""

import sqlite3
from pathlib import Path
from typing import Optional
from core.logger import get_logger

logger = get_logger(__name__)

# 数据库路径
DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "rewind.db"
SCHEMA_PATH = DB_DIR / "schema.sql"


def init_database(db_path: Optional[Path] = None) -> None:
    """
    初始化数据库，创建所有表

    Args:
        db_path: 数据库文件路径，默认使用DB_PATH
    """
    if db_path is None:
        db_path = DB_PATH

    try:
        logger.info(f"开始初始化数据库: {db_path}")

        # 确保目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取schema
        if not SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema文件不存在: {SCHEMA_PATH}")

        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # 执行schema
        with sqlite3.connect(db_path) as conn:
            conn.executescript(schema_sql)
            conn.commit()

        logger.info(f"数据库初始化成功: {db_path}")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    获取数据库连接

    Args:
        db_path: 数据库文件路径，默认使用DB_PATH

    Returns:
        数据库连接对象
    """
    if db_path is None:
        db_path = DB_PATH

    # 如果数据库不存在，先初始化
    if not db_path.exists():
        logger.warning(f"数据库不存在，自动初始化: {db_path}")
        init_database(db_path)

    conn = sqlite3.connect(db_path)
    # 启用行工厂，使查询结果可以通过列名访问
    conn.row_factory = sqlite3.Row
    return conn


def execute_query(query: str, params: tuple = (), db_path: Optional[Path] = None):
    """
    执行查询语句

    Args:
        query: SQL查询语句
        params: 查询参数
        db_path: 数据库路径

    Returns:
        查询结果列表
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def execute_update(query: str, params: tuple = (), db_path: Optional[Path] = None) -> int:
    """
    执行更新语句（INSERT, UPDATE, DELETE）

    Args:
        query: SQL语句
        params: 参数
        db_path: 数据库路径

    Returns:
        受影响的行数
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
