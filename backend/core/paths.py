"""
Path utility module
Provides reliable path finding functionality across environments (development/Tauri packaged)
"""

import os
from pathlib import Path
from typing import List, Optional

from core.logger import get_logger

logger = get_logger(__name__)


def get_backend_root() -> Path:
    """
    Get the root path of the backend directory
    Try multiple possible locations to support different runtime environments
    """
    search_paths: List[Optional[Path]] = [
        # 1. Infer from current file location (core/paths.py -> backend/)
        Path(__file__).parent.parent,
        # 2. Backend directory in current working directory
        Path.cwd() / "backend",
        # 3. Current working directory is backend
        Path.cwd() if (Path.cwd() / "core").exists() else None,
    ]

    for path in search_paths:
        if path and path.exists() and (path / "core").exists():
            logger.debug(f"Found backend root directory: {path}")
            return path

    # Fallback: return the first candidate path (guaranteed to be Path, not None)
    default_path = Path(__file__).parent.parent
    logger.warning(
        f"Unable to determine backend root directory, using default path: {default_path}"
    )
    return default_path


def find_config_file(
    filename: str, subdirs: Optional[List[str]] = None
) -> Optional[Path]:
    """
    Find configuration file

    Args:
        filename: Configuration file name (e.g., "config.toml")
        subdirs: Optional list of subdirectories (e.g., ["config"])

    Returns:
        Complete path to the configuration file, return None if not found
    """
    backend_root = get_backend_root()
    subdirs = subdirs or []

    # Build search paths
    search_paths = [
        # 1. backend/config/filename
        backend_root / "config" / filename,
        # 2. backend/filename
        backend_root / filename,
        # 3. Current working directory/config/filename
        Path.cwd() / "config" / filename,
        # 4. Current working directory/filename
        Path.cwd() / filename,
    ]

    # Add additional subdirectory searches
    for subdir in subdirs:
        search_paths.append(backend_root / subdir / filename)
        search_paths.append(Path.cwd() / subdir / filename)

    for path in search_paths:
        if path.exists():
            logger.info(f"Found configuration file: {path}")
            return path

    logger.warning(f"Configuration file not found: {filename}")
    return None


def ensure_dir(dir_path: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't

    Args:
        dir_path: Directory path

    Returns:
        Directory path
    """
    dir_path = Path(dir_path)
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")
    return dir_path


def get_data_dir(subdir: Optional[str] = None) -> Path:
    """
    Get data directory (for storing databases, logs, temporary files, etc.)

    Priority:
    1. ~/.config/ido under user home directory (follows user's standard config directory)
    2. data directory under project root
    3. backend/data

    Args:
        subdir: Optional subdirectory name

    Returns:
        Data directory path
    """
    # Prioritize using standard config directory under user home
    user_config_dir = Path.home() / ".config" / "ido"

    if (
        user_config_dir.exists() or True
    ):  # Always use user config directory as first choice
        data_dir = user_config_dir
        logger.debug(f"Using user config directory: {data_dir}")
    else:
        # Fallback: data directory under project root
        backend_root = get_backend_root()
        data_dir = backend_root.parent / "data"

        # If doesn't exist, use backend/data
        if not data_dir.exists():
            data_dir = backend_root / "data"

        logger.debug(f"Using project data directory: {data_dir}")

    # Add subdirectory
    if subdir:
        data_dir = data_dir / subdir

    return ensure_dir(data_dir)


def get_logs_dir() -> Path:
    """Get logs directory"""
    return get_data_dir("logs")


def get_tmp_dir(subdir: Optional[str] = None) -> Path:
    """
    Get temporary file directory

    Args:
        subdir: Optional subdirectory name (e.g., "screenshots")

    Returns:
        Temporary directory path
    """
    tmp_dir = get_data_dir("tmp")
    if subdir:
        tmp_dir = tmp_dir / subdir
    return ensure_dir(tmp_dir)


def get_db_path(db_name: str = "ido.db") -> Path:
    """
    Get database file path

    Args:
        db_name: Database file name

    Returns:
        Database file path
    """
    return get_data_dir() / db_name
