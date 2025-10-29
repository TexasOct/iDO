"""
路径工具模块
提供跨环境（开发/Tauri打包）的可靠路径查找功能
"""

import os
from pathlib import Path
from typing import Optional, List
from core.logger import get_logger

logger = get_logger(__name__)


def get_backend_root() -> Path:
    """
    获取 backend 目录的根路径
    尝试多个可能的位置以支持不同的运行环境
    """
    search_paths = [
        # 1. 从当前文件位置推断（core/paths.py -> backend/）
        Path(__file__).parent.parent,
        # 2. 当前工作目录下的 backend
        Path.cwd() / "backend",
        # 3. 当前工作目录就是 backend
        Path.cwd() if (Path.cwd() / "core").exists() else None,
    ]

    for path in search_paths:
        if path and path.exists() and (path / "core").exists():
            logger.debug(f"找到 backend 根目录: {path}")
            return path

    # 降级：返回第一个候选路径
    default_path = search_paths[0]
    logger.warning(f"无法确定 backend 根目录，使用默认路径: {default_path}")
    return default_path


def find_config_file(filename: str, subdirs: Optional[List[str]] = None) -> Optional[Path]:
    """
    查找配置文件

    Args:
        filename: 配置文件名（如 "config.toml"）
        subdirs: 可选的子目录列表（如 ["config"]）

    Returns:
        配置文件的完整路径，如果找不到则返回 None
    """
    backend_root = get_backend_root()
    subdirs = subdirs or []

    # 构建搜索路径
    search_paths = [
        # 1. backend/config/filename
        backend_root / "config" / filename,
        # 2. backend/filename
        backend_root / filename,
        # 3. 当前工作目录/config/filename
        Path.cwd() / "config" / filename,
        # 4. 当前工作目录/filename
        Path.cwd() / filename,
    ]

    # 添加额外的子目录搜索
    for subdir in subdirs:
        search_paths.append(backend_root / subdir / filename)
        search_paths.append(Path.cwd() / subdir / filename)

    for path in search_paths:
        if path.exists():
            logger.info(f"找到配置文件: {path}")
            return path

    logger.warning(f"未找到配置文件: {filename}")
    return None


def ensure_dir(dir_path: Path) -> Path:
    """
    确保目录存在，不存在则创建

    Args:
        dir_path: 目录路径

    Returns:
        目录路径
    """
    dir_path = Path(dir_path)
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录: {dir_path}")
    return dir_path


def get_data_dir(subdir: Optional[str] = None) -> Path:
    """
    获取数据目录（用于存储数据库、日志、临时文件等）

    优先级：
    1. 用户主目录下的 ~/.config/rewind （跟随用户的标准配置目录）
    2. 项目根目录下的 data 目录
    3. backend/data

    Args:
        subdir: 可选的子目录名

    Returns:
        数据目录路径
    """
    # 优先使用用户主目录下的标准配置目录
    user_config_dir = Path.home() / ".config" / "rewind"

    if user_config_dir.exists() or True:  # 总是使用用户配置目录作为首选
        data_dir = user_config_dir
        logger.debug(f"使用用户配置目录: {data_dir}")
    else:
        # 备用方案：项目根目录下的 data 目录
        backend_root = get_backend_root()
        data_dir = backend_root.parent / "data"

        # 如果不存在，使用 backend/data
        if not data_dir.exists():
            data_dir = backend_root / "data"

        logger.debug(f"使用项目数据目录: {data_dir}")

    # 添加子目录
    if subdir:
        data_dir = data_dir / subdir

    return ensure_dir(data_dir)


def get_logs_dir() -> Path:
    """获取日志目录"""
    return get_data_dir("logs")


def get_tmp_dir(subdir: Optional[str] = None) -> Path:
    """
    获取临时文件目录

    Args:
        subdir: 可选的子目录名（如 "screenshots"）

    Returns:
        临时目录路径
    """
    tmp_dir = get_data_dir("tmp")
    if subdir:
        tmp_dir = tmp_dir / subdir
    return ensure_dir(tmp_dir)


def get_db_path(db_name: str = "rewind.db") -> Path:
    """
    获取数据库文件路径

    Args:
        db_name: 数据库文件名

    Returns:
        数据库文件路径
    """
    return get_data_dir() / db_name
