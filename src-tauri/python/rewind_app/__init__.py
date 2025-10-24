from os import getenv
from pathlib import Path

from anyio.from_thread import start_blocking_portal
from pydantic.alias_generators import to_camel
from pytauri import (
    Commands,
    builder_factory,
    context_factory,
)

# Import the automatic command registration function
from rewind_backend.handlers import register_pytauri_commands

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
    import time

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
        from rewind_backend.core.events import register_emit_handler

        log_main("即将注册 Tauri AppHandle 用于事件发送...")
        register_emit_handler(app.handle())
        log_main("✅ Tauri AppHandle 注册完成")

        log_main("开始运行 Tauri 应用...")
        exit_code = app.run_return()

        # ⭐ Ensure backend is gracefully stopped when app exits
        # Run cleanup in a background thread to avoid blocking window close
        log_main("Tauri 应用已退出，清理后端资源...")
        try:
            import threading
            import asyncio
            from rewind_backend.core.coordinator import get_coordinator
            from rewind_backend.system.runtime import stop_runtime

            def cleanup_backend():
                """Clean up backend in a separate thread"""
                try:
                    coordinator = get_coordinator()
                    if coordinator.is_running:
                        log_main("协调器仍在运行，正在停止...")
                        sys.stderr.flush()
                        # Create a new event loop for this thread
                        asyncio.run(stop_runtime(quiet=True))
                        log_main("✅ 后端已停止")
                        sys.stderr.flush()
                    else:
                        log_main("协调器未运行，无需清理")
                        sys.stderr.flush()
                except Exception as e:
                    log_main(f"后端清理异常: {e}")
                    sys.stderr.flush()

            # Start cleanup in background thread (don't block window close)
            cleanup_thread = threading.Thread(target=cleanup_backend, daemon=False)
            cleanup_thread.start()

            # Wait for cleanup with timeout (5 seconds max)
            cleanup_thread.join(timeout=5.0)
            if cleanup_thread.is_alive():
                log_main("⚠️  后端清理超时，但允许应用退出")
                sys.stderr.flush()
            else:
                log_main("✅ 清理线程已完成")
                sys.stderr.flush()

        except Exception as e:
            log_main(f"启动清理线程异常: {e}")
            sys.stderr.flush()

        log_main("应用返回退出码，进程结束")
        sys.stderr.flush()
        return exit_code
