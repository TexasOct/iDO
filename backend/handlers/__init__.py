"""
Handler modules with automatic API registration
Supports automatic API registration
Supports both PyTauri and FastAPI frameworks
"""

import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
)

if TYPE_CHECKING:
    from fastapi import FastAPI
    from pytauri import Commands

F = TypeVar('F', bound=Callable[..., Any])

# Global API handler registry
_handler_registry: Dict[str, Dict[str, Any]] = {}


def api_handler(
    body: Optional[Type] = None,
    method: str = "POST",
    path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
):
    """
    Universal API handler decorator for multiple backend frameworks

    @param body - Optional request model type for parameter validation
    @param method - HTTP method (GET, POST, PUT, DELETE, etc.)
    @param path - Custom path (FastAPI only)
    @param tags - API tags (FastAPI only)
    @param summary - API summary
    @param description - API description
    """

    def decorator(func: F) -> F:
        # Get function information
        func_name = getattr(func, '__name__', 'unknown')
        func_module = getattr(func, '__module__', '')
        module_name = func_module.split(".")[-1] if func_module else 'unknown'
        func_doc = getattr(func, '__doc__', None)

        # Register handler information
        _handler_registry[func_name] = {
            "func": func,
            "body": body,
            "method": method.upper(),
            "path": path or f"/{func_name}",
            "tags": tags or [module_name],
            "module": module_name,
            "summary": summary or (func_doc.split("\n")[0] if func_doc else func_name),
            "description": description or func_doc or "",
            "docstring": func_doc or "",
            "signature": inspect.signature(func),
        }

        # Keep original function unchanged
        return func

    return decorator


def get_registered_handlers() -> Dict[str, Dict[str, Any]]:
    """
    Get registered handler information (for debugging)

    @returns Handler registry
    """
    return _handler_registry.copy()


def register_pytauri_commands(commands: "Commands") -> None:
    """
    Automatically register all functions decorated with @api_handler as PyTauri commands

    @param commands - PyTauri Commands instance
    """
    import logging

    logger = logging.getLogger(__name__)

    logger.info(
        f"Starting PyTauri command registration, {len(_handler_registry)} handlers"
    )

    # Iterate through registry and automatically register all commands
    for handler_name, handler_info in _handler_registry.items():
        func = handler_info["func"]
        body = handler_info.get("body")
        module = handler_info.get("module", "unknown")

        try:
            # PyTauri's commands.command() decorator automatically handles function parameters

            if body:
                logger.debug(
                    f"Register command (with Pydantic model): {handler_name} from {module}, body={body.__name__}"
                )

                # Create a wrapper with explicit type annotations for PyTauri to extract
                # Get original function return type
                orig_annotations = getattr(func, "__annotations__", {})
                return_type = orig_annotations.get("return", type(None))

                # Create new function, explicitly preserving type annotations
                def make_wrapper(original_func, body_model, return_type_hint):
                    async def wrapper(body):  # type: ignore
                        return await original_func(body)

                    # Explicitly set annotations so PyTauri can correctly extract type information
                    wrapper.__annotations__ = {
                        "body": body_model,
                        "return": return_type_hint,
                    }
                    # Copy documentation and names
                    wrapper.__doc__ = original_func.__doc__
                    wrapper.__name__ = original_func.__name__
                    return wrapper

                wrapped_func = make_wrapper(func, body, return_type)
                commands.command()(wrapped_func)
            else:
                logger.debug(
                    f"Register command (no params): {handler_name} from {module}"
                )
                # Directly register function, PyTauri will automatically handle based on function signature
                commands.command()(func)

            logger.info(f"✓ Successfully registered: {handler_name}")

        except Exception as e:
            logger.error(
                f"✗ Failed to register command {handler_name}: {e}", exc_info=True
            )

    logger.info(
        f"PyTauri command registration completed: {len(_handler_registry)} commands"
    )


def register_fastapi_routes(app: "FastAPI", prefix: str = "/api") -> None:
    """
    Automatically register all functions decorated with @api_handler as FastAPI routes

    @param app - FastAPI application instance
    @param prefix - Route prefix
    """
    import logging

    logger = logging.getLogger(__name__)

    logger.info(
        f"Starting FastAPI route registration, {len(_handler_registry)} handlers"
    )

    # Iterate through registry and automatically register all routes
    for handler_name, handler_info in _handler_registry.items():
        func = handler_info["func"]
        body = handler_info.get("body")  # noqa
        method = handler_info.get("method", "POST")
        path = handler_info.get("path", f"/{handler_name}")
        tags = handler_info.get("tags", [])
        summary = handler_info.get("summary", handler_name)
        description = handler_info.get("description", "")
        module = handler_info.get("module", "unknown")

        try:
            # Build full path
            full_path = f"{prefix}{path}"

            # Register route based on HTTP method
            # Note: route_params uses cast to ensure type compatibility with FastAPI
            route_params: Dict[str, Any] = {
                "path": full_path,
                "tags": tags,
                "summary": summary,
                "description": description,
                "response_model": None,  # Can be automatically inferred from return type
            }

            if method == "GET":
                app.get(**route_params)(func)  # type: ignore
            elif method == "POST":
                app.post(**route_params)(func)  # type: ignore
            elif method == "PUT":
                app.put(**route_params)(func)  # type: ignore
            elif method == "DELETE":
                app.delete(**route_params)(func)  # type: ignore
            elif method == "PATCH":
                app.patch(**route_params)(func)  # type: ignore
            else:
                logger.warning(f"Unknown HTTP method: {method} for {handler_name}")
                continue

            logger.info(
                f"✓ Successfully registered route: {method} {full_path} ({handler_name} from {module})"
            )

        except Exception as e:
            logger.error(
                f"✗ Failed to register route {handler_name}: {e}", exc_info=True
            )

    logger.info(
        f"FastAPI route registration completed: {len(_handler_registry)} routes"
    )


# Import all handler modules to trigger decorator registration
# Note: These imports must be after all decorator definitions to avoid circular imports
# ruff: noqa: E402
from . import (
    agents,
    chat,
    dashboard,
    friendly_chat,
    greeting,
    image,
    insights,
    live2d,
    models_management,
    perception,
    permissions,
    processing,
    screens,
    system,
    tray,
)

__all__ = [
    "api_handler",
    "register_pytauri_commands",
    "register_fastapi_routes",
    "get_registered_handlers",
    "greeting",
    "perception",
    "processing",
    "system",
    "agents",
    "chat",
    "dashboard",
    "models_management",
    "insights",
    "live2d",
    "friendly_chat",
    "screens",
    "image",
    "permissions",
    "tray",
]
