"""
Handler modules with automatic API registration
支持自动 API 注册的处理器模块
Supports both PyTauri and FastAPI frameworks
"""

import inspect
from typing import Dict, Any, Callable, Optional, Type, List, TYPE_CHECKING

if TYPE_CHECKING:
    from pytauri import Commands
    from fastapi import FastAPI

# 全局 API handler 注册表
# Global API handler registry
_handler_registry: Dict[str, Dict[str, Any]] = {}


def api_handler(
    body: Optional[Type] = None,
    method: str = "POST",
    path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None
):
    """
    通用的 API handler 装饰器，支持多种后端框架
    Universal API handler decorator for multiple backend frameworks

    @param body - 可选的请求模型类型，用于参数验证和类型转换 / Optional request model type for parameter validation
    @param method - HTTP 方法 (GET, POST, PUT, DELETE等) / HTTP method (GET, POST, PUT, DELETE, etc.)
    @param path - 自定义路径 (仅 FastAPI) / Custom path (FastAPI only)
    @param tags - API 标签 (仅 FastAPI) / API tags (FastAPI only)
    @param summary - API 摘要 / API summary
    @param description - API 描述 / API description
    """
    def decorator(func: Callable) -> Callable:
        # 获取函数信息
        # Get function information
        func_name = func.__name__
        module_name = func.__module__.split('.')[-1]  # 获取模块名

        # 注册 handler 信息
        # Register handler information
        _handler_registry[func_name] = {
            'func': func,
            'body': body,
            'method': method.upper(),
            'path': path or f"/{func_name}",
            'tags': tags or [module_name],
            'module': module_name,
            'summary': summary or func.__doc__.split('\n')[0] if func.__doc__ else func_name,
            'description': description or func.__doc__ or "",
            'docstring': func.__doc__ or "",
            'signature': inspect.signature(func)
        }

        # 保持原函数不变
        # Keep original function unchanged
        return func

    return decorator


def get_registered_handlers() -> Dict[str, Dict[str, Any]]:
    """
    获取已注册的 handler 信息（用于调试）
    Get registered handler information (for debugging)

    @returns Handler 注册表 / Handler registry
    """
    return _handler_registry.copy()


def register_pytauri_commands(commands: "Commands") -> None:
    """
    自动注册所有被 @api_handler 装饰的函数为 PyTauri commands
    Automatically register all functions decorated with @api_handler as PyTauri commands

    @param commands - PyTauri Commands 实例 / PyTauri Commands instance
    """
    import logging
    logger = logging.getLogger(__name__)

    # 导入所有 handler 模块以触发装饰器注册
    # Import all handler modules to trigger decorator registration
    from . import greeting, perception, processing, system, agents, image, chat, models_management  # noqa: F401

    logger.info(f"开始注册 PyTauri 命令，共 {len(_handler_registry)} 个 / Starting PyTauri command registration, {len(_handler_registry)} handlers")

    # 遍历注册表，自动注册所有命令
    # Iterate through registry and automatically register all commands
    for handler_name, handler_info in _handler_registry.items():
        func = handler_info['func']
        body = handler_info.get('body')
        module = handler_info.get('module', 'unknown')

        try:
            # PyTauri 的 commands.command() 装饰器会自动处理函数参数
            # PyTauri's commands.command() decorator automatically handles function parameters

            if body:
                logger.debug(f"注册命令 (带Pydantic模型) / Register command (with Pydantic model): {handler_name} from {module}, body={body.__name__}")

                # ⭐ 关键修复：为了让 PyTauri 正确生成 JSON Schema，需要创建一个带有正确类型注解的包装函数
                # Create a wrapper with explicit type annotations for PyTauri to extract

                # 获取原函数的返回类型
                orig_annotations = getattr(func, '__annotations__', {})
                return_type = orig_annotations.get('return', type(None))

                # 创建新函数，显式保留类型注解
                def make_wrapper(original_func, body_model, return_type_hint):
                    async def wrapper(body):  # type: ignore
                        return await original_func(body)
                    # 显式设置注解，使 PyTauri 能够正确提取类型信息
                    wrapper.__annotations__ = {
                        'body': body_model,
                        'return': return_type_hint
                    }
                    # 复制文档和名称
                    wrapper.__doc__ = original_func.__doc__
                    wrapper.__name__ = original_func.__name__
                    return wrapper

                wrapped_func = make_wrapper(func, body, return_type)
                commands.command()(wrapped_func)
            else:
                logger.debug(f"注册命令 (无参数) / Register command (no params): {handler_name} from {module}")
                # 直接注册函数，PyTauri 会根据函数签名自动处理
                commands.command()(func)

            logger.info(f"✓ 成功注册命令 / Successfully registered: {handler_name}")

        except Exception as e:
            logger.error(f"✗ 注册命令失败 / Failed to register command {handler_name}: {e}", exc_info=True)

    logger.info(f"PyTauri 命令注册完成 / PyTauri command registration completed: {len(_handler_registry)} commands")


def register_fastapi_routes(app: "FastAPI", prefix: str = "/api") -> None:
    """
    自动注册所有被 @api_handler 装饰的函数为 FastAPI routes
    Automatically register all functions decorated with @api_handler as FastAPI routes

    @param app - FastAPI 应用实例 / FastAPI application instance
    @param prefix - 路由前缀 / Route prefix
    """
    import logging
    logger = logging.getLogger(__name__)

    # 导入所有 handler 模块以触发装饰器注册
    # Import all handler modules to trigger decorator registration
    from . import greeting, perception, processing, system, agents, image, chat, models_management  # noqa: F401

    logger.info(f"开始注册 FastAPI 路由，共 {len(_handler_registry)} 个 / Starting FastAPI route registration, {len(_handler_registry)} handlers")

    # 遍历注册表，自动注册所有路由
    # Iterate through registry and automatically register all routes
    for handler_name, handler_info in _handler_registry.items():
        func = handler_info['func']
        body = handler_info.get('body')
        method = handler_info.get('method', 'POST')
        path = handler_info.get('path', f"/{handler_name}")
        tags = handler_info.get('tags', [])
        summary = handler_info.get('summary', handler_name)
        description = handler_info.get('description', '')
        module = handler_info.get('module', 'unknown')

        try:
            # 构造完整路径
            # Build full path
            full_path = f"{prefix}{path}"

            # 根据 HTTP 方法注册路由
            # Register route based on HTTP method
            route_params = {
                'path': full_path,
                'tags': tags,
                'summary': summary,
                'description': description,
                'response_model': None,  # 可以根据返回类型自动推断
            }

            if method == 'GET':
                app.get(**route_params)(func)
            elif method == 'POST':
                app.post(**route_params)(func)
            elif method == 'PUT':
                app.put(**route_params)(func)
            elif method == 'DELETE':
                app.delete(**route_params)(func)
            elif method == 'PATCH':
                app.patch(**route_params)(func)
            else:
                logger.warning(f"未知的 HTTP 方法 / Unknown HTTP method: {method} for {handler_name}")
                continue

            logger.info(f"✓ 成功注册路由 / Successfully registered route: {method} {full_path} ({handler_name} from {module})")

        except Exception as e:
            logger.error(f"✗ 注册路由失败 / Failed to register route {handler_name}: {e}", exc_info=True)

    logger.info(f"FastAPI 路由注册完成 / FastAPI route registration completed: {len(_handler_registry)} routes")


# 导入所有 handler 模块以触发装饰器注册
from . import greeting, perception, processing, system, agents, image, chat, dashboard, models_management

__all__ = [
    'api_handler',
    'register_pytauri_commands',
    'register_fastapi_routes',
    'get_registered_handlers',
    'greeting',
    'perception',
    'processing',
    'system',
    'agents',
    'chat',
    'dashboard',
    'models_management'
]
