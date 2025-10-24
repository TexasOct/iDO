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

        print("[Main] 即将注册 Tauri AppHandle 用于事件发送...")
        register_emit_handler(app.handle())
        print("[Main] ✅ Tauri AppHandle 注册完成")

        exit_code = app.run_return()

        # ⭐ Ensure backend is gracefully stopped when app exits
        # This runs AFTER app.run_return() returns (when window is closed)
        # using a fresh event loop instead of the portal
        print("[Main] Tauri 应用已退出，清理后端资源...")
        try:
            import asyncio
            from rewind_backend.core.coordinator import get_coordinator
            from rewind_backend.system.runtime import stop_runtime

            coordinator = get_coordinator()
            if coordinator.is_running:
                print("[Main] 协调器仍在运行，正在停止...")
                # Use asyncio.run() to create a fresh event loop for cleanup
                asyncio.run(stop_runtime(quiet=True))
                print("[Main] ✅ 后端已停止")
            else:
                print("[Main] 协调器未运行，无需清理")
        except Exception as e:
            print(f"[Main] 后端清理异常: {e}")

        return exit_code
