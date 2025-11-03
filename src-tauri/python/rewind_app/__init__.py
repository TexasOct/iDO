import sys
from os import getenv
from pathlib import Path

from anyio.from_thread import start_blocking_portal
from pydantic.alias_generators import to_camel
from pytauri import (
    Commands,
    builder_factory,
    context_factory,
)

# 跨平台且跨环境的导入解决方案
# 开发环境：backend/ 在项目根目录
# 生产环境：rewind_backend/ 在 site-packages（通过 pyproject.toml 安装）
def _setup_backend_import():
    """设置 backend 模块的导入路径，支持开发和生产环境"""
    try:
        # 首先尝试导入 rewind_backend（生产环境）
        import rewind_backend
        return 'rewind_backend'
    except ImportError:
        # 如果失败，说明在开发环境，需要添加项目根目录到路径
        _current_dir = Path(__file__).parent  # src-tauri/python/rewind_app
        _python_dir = _current_dir.parent      # src-tauri/python
        _src_tauri_dir = _python_dir.parent    # src-tauri
        _project_root = _src_tauri_dir.parent  # 项目根目录

        # 添加项目根目录到 Python 路径
        if str(_project_root) not in sys.path:
            sys.path.insert(0, str(_project_root))

        # 验证是否可以导入 backend
        try:
            import backend
            return 'backend'
        except ImportError:
            raise ImportError(
                "无法导入 backend 模块。请确保：\n"
                "1. 开发环境：项目根目录存在 backend/ 文件夹\n"
                "2. 生产环境：rewind_backend 已通过 pyproject.toml 正确安装"
            )

# 动态确定使用哪个模块名
BACKEND_MODULE = _setup_backend_import()

# 根据环境动态导入
if BACKEND_MODULE == 'rewind_backend':
    from rewind_backend.handlers import register_pytauri_commands
else:
    from backend.handlers import register_pytauri_commands

# ⭐ You should only enable this feature in development (not production)
# 只有明确设置 PYTAURI_GEN_TS=1 时才启用（默认禁用）
# 这样在打包后的应用中会自动禁用
PYTAURI_GEN_TS = getenv("PYTAURI_GEN_TS") == "1"

# ⭐ Enable this feature first
commands = Commands(experimental_gen_ts=PYTAURI_GEN_TS)

# ⭐ Automatically register all API handlers as PyTauri commands
# 自动注册所有被 @api_handler 装饰的函数为 PyTauri 命令
register_pytauri_commands(commands)


def main() -> int:
    import sys

    # Enable unbuffered output for reliable logging
    def log_main(msg):
        """Reliable logging using stderr with flush"""
        sys.stderr.write(f"[Main] {msg}\n")
        sys.stderr.flush()

    with start_blocking_portal("asyncio") as portal:
        if PYTAURI_GEN_TS:
            # ⭐ Generate TypeScript Client to your frontend `src/client` directory
            output_dir = Path(__file__).parent.parent.parent.parent / "src" / "lib" / "client"
            # ⭐ The CLI to run `json-schema-to-typescript`,
            # `--format=false` is optional to improve performance
            json2ts_cmd = "pnpm json2ts --format=false"

            # ⭐ Start the background task to generate TypeScript types
            portal.start_task_soon(
                lambda: commands.experimental_gen_ts_background(
                    output_dir, json2ts_cmd, cmd_alias=to_camel
                )
            )

        context = context_factory()

        app = builder_factory().build(
            context=context,
            invoke_handler=commands.generate_handler(portal),
        )

        # ⭐ Register Tauri AppHandle for backend event emission using pytauri.Emitter
        if BACKEND_MODULE == 'rewind_backend':
            from rewind_backend.core.events import register_emit_handler
        else:
            from backend.core.events import register_emit_handler

        log_main("即将注册 Tauri AppHandle 用于事件发送...")
        register_emit_handler(app.handle())
        log_main("✅ Tauri AppHandle 注册完成")

        log_main("开始运行 Tauri 应用...")
        exit_code = app.run_return()

        # ⭐ Ensure backend is gracefully stopped when app exits
        # Run cleanup in a background thread to avoid blocking window close
        log_main("Tauri 应用已退出，清理后端资源...")
        cleanup_thread = None

        try:
            import threading
            import asyncio

            if BACKEND_MODULE == 'rewind_backend':
                from rewind_backend.core.coordinator import get_coordinator
                from rewind_backend.system.runtime import stop_runtime
            else:
                from backend.core.coordinator import get_coordinator
                from backend.system.runtime import stop_runtime

            cleanup_completed = threading.Event()

            def cleanup_backend():
                """Clean up backend in a separate thread"""
                try:
                    coordinator = get_coordinator()
                    if coordinator.is_running:
                        log_main("协调器仍在运行，正在停止...")
                        sys.stderr.flush()
                        # Create a new event loop for this thread with shorter timeout
                        try:
                            # 给 asyncio 更多时间（3.5 秒），但不超过线程总超时（4 秒）
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(stop_runtime(quiet=True))
                            loop.close()
                            log_main("✅ 后端已停止")
                        except Exception as inner_e:
                            log_main(f"⚠️  后端停止出错，继续: {inner_e}")
                        finally:
                            sys.stderr.flush()
                    else:
                        log_main("协调器未运行，无需清理")
                        sys.stderr.flush()
                except Exception as e:
                    log_main(f"后端清理异常: {e}")
                    sys.stderr.flush()
                finally:
                    cleanup_completed.set()

            # Start cleanup in background thread (don't block window close)
            cleanup_thread = threading.Thread(target=cleanup_backend, daemon=False)
            cleanup_thread.start()

            # Wait for cleanup with timeout (4 seconds max)
            # Give 4 seconds for cleanup, which is less than the 5 second wait_for in coordinator
            if cleanup_completed.wait(timeout=4.0):
                log_main("✅ 清理线程已完成")
            else:
                log_main("⚠️  后端清理超时，但允许应用退出")
            sys.stderr.flush()

        except Exception as e:
            log_main(f"启动清理线程异常: {e}")
            sys.stderr.flush()

        # Ensure thread doesn't block process exit
        # 给线程 1 秒的时间来完成，之后继续退出
        if cleanup_thread is not None:
            cleanup_thread.join(timeout=1.0)

        log_main("应用开始退出，进程结束")
        sys.stderr.flush()
        return exit_code
