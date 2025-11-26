import sys
from importlib import import_module
from os import getenv
from pathlib import Path

from anyio.from_thread import start_blocking_portal
from pydantic.alias_generators import to_camel
from pytauri import (
    Commands,
    builder_factory,
    context_factory,
)


# Cross-platform and cross-environment import solution
# Development: backend/ in project root
# Production: ido_backend/ in site-packages (installed via pyproject.toml)
def _setup_backend_import():
    """Setup backend module import path for both dev and production environments"""
    try:
        # First try to import ido_backend (production environment)
        import_module("ido_backend")
        return "ido_backend"
    except ImportError:
        # If failed, we're in development environment, add project root to path
        _current_dir = Path(__file__).parent  # src-tauri/python/ido_app
        _python_dir = _current_dir.parent  # src-tauri/python
        _src_tauri_dir = _python_dir.parent  # src-tauri
        _project_root = _src_tauri_dir.parent  # project root

        # Add project root to Python path
        if str(_project_root) not in sys.path:
            sys.path.insert(0, str(_project_root))

        # Verify backend can be imported
        try:
            import_module("backend")
            return "backend"
        except ImportError:
            raise ImportError(
                "Cannot import backend module. Please ensure:\n"
                "1. Development: backend/ folder exists in project root\n"
                "2. Production: ido_backend is properly installed via pyproject.toml"
            )


# Dynamically determine which module to use
BACKEND_MODULE = _setup_backend_import()


# Dynamic import helper based on environment
def _backend_module_path(suffix: str) -> str:
    prefix = "ido_backend" if BACKEND_MODULE == "ido_backend" else "backend"
    return f"{prefix}.{suffix}"


register_pytauri_commands = getattr(
    import_module(_backend_module_path("handlers")), "register_pytauri_commands"
)

# ⭐ You should only enable this feature in development (not production)
# Only enabled when PYTAURI_GEN_TS=1 is explicitly set (disabled by default)
# This automatically disables in packaged applications
PYTAURI_GEN_TS = getenv("PYTAURI_GEN_TS") == "1"

# ⭐ Enable this feature first
commands = Commands(experimental_gen_ts=PYTAURI_GEN_TS)

# ⭐ Automatically register all API handlers as PyTauri commands
# Auto-register all @api_handler decorated functions as PyTauri commands
register_pytauri_commands(commands)


def main() -> int:
    import sys

    # Enable unbuffered output for reliable logging
    def log_main(msg: str) -> None:
        """Reliable logging that works when stdout/stderr are disconnected.

        - Try to write to sys.stderr if available.
        - Fallback: append to a log file in the user's local app data folder.
        """
        try:
            # 优先写 stderr（如果可用）
            stderr = getattr(sys, "stderr", None)
            if stderr is not None and hasattr(stderr, "write"):
                stderr.write(f"[Main] {msg}\n")
                try:
                    stderr.flush()
                except Exception:
                    pass
                return

            # 回退到文件
            try:
                from os import getenv
                from pathlib import Path

                # 在 Windows 下优先使用 LOCALAPPDATA；跨平台可以用 HOME/.config
                local_appdata = (
                    getenv("LOCALAPPDATA")
                    or getenv("XDG_CONFIG_HOME")
                    or str(Path.home())
                )
                log_dir = Path(local_appdata) / "iDO"
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / "ido.log"
                with log_file.open("a", encoding="utf-8") as fh:
                    fh.write(f"[Main] {msg}\n")
            except Exception:
                # 最后一招：如果连写文件也失败，尝试调用 Windows OutputDebugString（无害，仅在 Windows 有效果）
                try:
                    if sys.platform.startswith("win"):
                        import ctypes

                        ctypes.windll.kernel32.OutputDebugStringW(f"[Main] {msg}\n")
                except Exception:
                    # 避免任何二次错误导致主流程退出
                    pass
        except Exception:
            # 绝对不要让 logging 自己崩溃
            try:
                # 最后尝试用 print（可能也无效）
                print(f"[Main] {msg}")
            except Exception:
                pass

    with start_blocking_portal("asyncio") as portal:
        if PYTAURI_GEN_TS:
            # ⭐ Generate TypeScript Client to your frontend `src/client` directory
            output_dir = (
                Path(__file__).parent.parent.parent.parent / "src" / "lib" / "client"
            )
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
        register_emit_handler = getattr(
            import_module(_backend_module_path("core.events")), "register_emit_handler"
        )

        log_main("Registering Tauri AppHandle for event emission...")
        register_emit_handler(app.handle())
        log_main("✅ Tauri AppHandle registered successfully")

        log_main("Starting Tauri application...")
        exit_code = app.run_return()

        # ⭐ Ensure backend is gracefully stopped when app exits
        log_main("Tauri application exited, cleaning up backend resources...")

        try:
            get_coordinator = getattr(
                import_module(_backend_module_path("core.coordinator")),
                "get_coordinator",
            )
            stop_runtime = getattr(
                import_module(_backend_module_path("system.runtime")), "stop_runtime"
            )

            import asyncio

            async def _stop_backend():
                """Stop runtime with a hard timeout to avoid exit hangs."""
                coordinator = get_coordinator()
                if not coordinator.is_running:
                    log_main("Coordinator not running, no cleanup needed")
                    return

                log_main("Coordinator is still running, stopping...")
                try:
                    # Hard timeout to prevent exit hang; stop_runtime has its own timeout but we guard it too.
                    await asyncio.wait_for(stop_runtime(quiet=True), timeout=3.5)
                    log_main("✅ Backend stopped successfully")
                except asyncio.TimeoutError:
                    log_main("⚠️  Backend stop timed out, forcing exit")
                except Exception as inner_e:
                    log_main(f"⚠️  Backend stop error, continuing: {inner_e}")

            # Run cleanup inside the existing portal event loop to avoid stray threads
            portal.call(_stop_backend)
            sys.stderr.flush()

        except Exception as e:
            log_main(f"Cleanup error: {e}")
            sys.stderr.flush()

        log_main("Application exiting, process ending")
        sys.stderr.flush()
        return exit_code
