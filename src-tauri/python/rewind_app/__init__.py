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

        app = builder_factory().build(
            context=context_factory(),
            invoke_handler=commands.generate_handler(portal),
        )
        exit_code = app.run_return()
        return exit_code