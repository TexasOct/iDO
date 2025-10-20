"""
Handler modules with automatic command registration
支持自动命令注册的处理器模块
"""

import inspect
from typing import Dict, Any, Callable, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from pytauri import Commands

# 全局命令注册表
_command_registry: Dict[str, Dict[str, Any]] = {}


def tauri_command(body: Optional[Type] = None):
    """
    装饰器，用于标记需要暴露为 Tauri command 的函数
    
    @param body - 可选的请求模型类型，用于参数验证和类型转换
    """
    def decorator(func: Callable) -> Callable:
        # 获取函数信息
        func_name = func.__name__
        module_name = func.__module__.split('.')[-1]  # 获取模块名
        
        # 注册命令信息
        _command_registry[func_name] = {
            'func': func,
            'body': body,
            'module': module_name,
            'docstring': func.__doc__ or "",
            'signature': inspect.signature(func)
        }
        
        # 保持原函数不变
        return func
    
    return decorator


def register_commands(commands: "Commands") -> None:
    """
    自动注册所有被 @tauri_command 装饰的函数为 Tauri commands
    
    @param commands - PyTauri Commands 实例
    """
    # 导入所有需要的模块
    from . import greeting, perception, processing
    from rewind_backend.models import (
        Person,
        GetRecordsRequest,
        GetEventsRequest, 
        GetActivitiesRequest,
        GetEventByIdRequest,
        GetActivityByIdRequest,
        CleanupOldDataRequest,
    )
    
    # 手动注册每个命令，保持与原来相同的逻辑
    # Demo command
    @commands.command()
    async def greet_to_person(body: Person) -> str:
        """A simple command that returns a greeting message.

        @param body - The person to greet.
        """
        return await greeting.greeting(body.name)
    
    # Perception commands
    @commands.command()
    async def get_perception_stats() -> Dict[str, Any]:
        """Get perception module statistics.

        Returns statistics about the perception module including record counts and status.
        """
        return await perception.get_perception_stats()
    
    @commands.command()
    async def get_records(body: GetRecordsRequest) -> Dict[str, Any]:
        """Get perception records with optional filters.

        @param body - Request parameters including limit and filters.
        """
        return await perception.get_records(
            limit=body.limit,
            event_type=body.event_type,
            start_time=body.start_time,
            end_time=body.end_time
        )
    
    @commands.command()
    async def start_perception() -> Dict[str, Any]:
        """Start the perception module.

        Starts monitoring keyboard, mouse, and screenshots.
        """
        return await perception.start_perception()
    
    @commands.command()
    async def stop_perception() -> Dict[str, Any]:
        """Stop the perception module.

        Stops monitoring keyboard, mouse, and screenshots.
        """
        return await perception.stop_perception()
    
    @commands.command()
    async def clear_records() -> Dict[str, Any]:
        """Clear all perception records.

        Removes all stored records and clears the buffer.
        """
        return await perception.clear_records()
    
    @commands.command()
    async def get_buffered_events() -> Dict[str, Any]:
        """Get buffered events.

        Returns events currently in the buffer waiting to be processed.
        """
        return await perception.get_buffered_events()
    
    # Processing commands
    @commands.command()
    async def get_processing_stats() -> Dict[str, Any]:
        """Get processing module statistics.

        Returns statistics about event and activity processing.
        """
        return await processing.get_processing_stats()
    
    @commands.command()
    async def get_events(body: GetEventsRequest) -> Dict[str, Any]:
        """Get processed events with optional filters.

        @param body - Request parameters including limit and filters.
        """
        return await processing.get_events(
            limit=body.limit,
            event_type=body.event_type,
            start_time=body.start_time,
            end_time=body.end_time
        )
    
    @commands.command()
    async def get_activities(body: GetActivitiesRequest) -> Dict[str, Any]:
        """Get processed activities.

        @param body - Request parameters including limit.
        """
        return await processing.get_activities(limit=body.limit)
    
    @commands.command()
    async def get_event_by_id(body: GetEventByIdRequest) -> Dict[str, Any]:
        """Get event details by ID.

        @param body - Request parameters including event ID.
        """
        return await processing.get_event_by_id(event_id=body.event_id)
    
    @commands.command()
    async def get_activity_by_id(body: GetActivityByIdRequest) -> Dict[str, Any]:
        """Get activity details by ID.

        @param body - Request parameters including activity ID.
        """
        return await processing.get_activity_by_id(activity_id=body.activity_id)
    
    @commands.command()
    async def start_processing() -> Dict[str, Any]:
        """Start the processing pipeline.

        Begins processing raw records into events and activities.
        """
        return await processing.start_processing()
    
    @commands.command()
    async def stop_processing() -> Dict[str, Any]:
        """Stop the processing pipeline.

        Stops processing raw records.
        """
        return await processing.stop_processing()
    
    @commands.command()
    async def finalize_current_activity() -> Dict[str, Any]:
        """Force finalize the current activity.

        Forces the completion of the current activity being processed.
        """
        return await processing.finalize_current_activity()
    
    @commands.command()
    async def cleanup_old_data(body: CleanupOldDataRequest) -> Dict[str, Any]:
        """Clean up old data.

        @param body - Request parameters including number of days to keep.
        """
        return await processing.cleanup_old_data(days=body.days)
    
    @commands.command()
    async def get_persistence_stats() -> Dict[str, Any]:
        """Get persistence statistics.

        Returns statistics about data persistence including database size and record counts.
        """
        return await processing.get_persistence_stats()


def get_registered_commands() -> Dict[str, Dict[str, Any]]:
    """
    获取已注册的命令信息（用于调试）
    
    @returns 命令注册表
    """
    return _command_registry.copy()


# 导入所有 handler 模块以触发装饰器注册
from . import greeting, perception, processing

__all__ = [
    'tauri_command',
    'register_commands', 
    'get_registered_commands',
    'greeting',
    'perception', 
    'processing'
]
