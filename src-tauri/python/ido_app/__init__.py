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
    def log_main(msg):
        """Reliable logging using stderr with flush"""
        sys.stderr.write(f"[Main] {msg}\n")
        sys.stderr.flush()

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
        # Run cleanup in a background thread to avoid blocking window close
        log_main("Tauri application exited, cleaning up backend resources...")
        cleanup_thread = None

        try:
            import asyncio
            import threading

            get_coordinator = getattr(
                import_module(_backend_module_path("core.coordinator")),
                "get_coordinator",
            )
            stop_runtime = getattr(
                import_module(_backend_module_path("system.runtime")), "stop_runtime"
            )

            cleanup_completed = threading.Event()

            def cleanup_backend():
                """Clean up backend in a separate thread"""
                try:
                    coordinator = get_coordinator()
                    if coordinator.is_running:
                        log_main("Coordinator is still running, stopping...")
                        sys.stderr.flush()
                        # Create a new event loop for this thread with shorter timeout
                        try:
                            # Give asyncio more time (3.5s), but not exceeding thread total timeout (4s)
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(stop_runtime(quiet=True))
                            loop.close()
                            log_main("✅ Backend stopped successfully")
                        except Exception as inner_e:
                            log_main(f"⚠️  Backend stop error, continuing: {inner_e}")
                        finally:
                            sys.stderr.flush()
                    else:
                        log_main("Coordinator not running, no cleanup needed")
                        sys.stderr.flush()
                except Exception as e:
                    log_main(f"Backend cleanup exception: {e}")
                    sys.stderr.flush()
                finally:
                    cleanup_completed.set()

            # Start cleanup in background thread (don't block window close)
            cleanup_thread = threading.Thread(target=cleanup_backend, daemon=False)
            cleanup_thread.start()

            # Wait for cleanup with timeout (4 seconds max)
            # Give 4 seconds for cleanup, which is less than the 5 second wait_for in coordinator
            if cleanup_completed.wait(timeout=4.0):
                log_main("✅ Cleanup thread completed")
            else:
                log_main("⚠️  Backend cleanup timeout, but allowing app to exit")
            sys.stderr.flush()

        except Exception as e:
            log_main(f"Cleanup thread startup exception: {e}")
            sys.stderr.flush()

        # Ensure thread doesn't block process exit
        # Give thread 1 second to complete, then continue exit
        if cleanup_thread is not None:
            cleanup_thread.join(timeout=1.0)

        log_main("Application exiting, process ending")
        sys.stderr.flush()
        return exit_code
