# Python Environment — Rewind

This document explains how the Python environment for Rewind is organized and the common commands/workflow you should use during development.

Important summary
- `pyproject.toml` is located at the project root — this is the authoritative Python project configuration.
- The project's virtual environment (`.venv`) is created at the project root.
- Always run environment sync / backend setup commands from the project root.
- After changing Python handlers/models, re-sync the Python environment and regenerate the frontend TypeScript client before running the app.

Recommended Python
- Use the Python version specified in `pyproject.toml` (recommended: 3.10+).
- Use the system `python`/`python3` that matches the version, or configure your IDE to use the project's `.venv`.

Prerequisites
- Python (matching project requirement)
- Node / pnpm (frontend tooling)
- Rust toolchain (for Tauri builds) — only required for desktop development/build
- Command-line virtual environment helper used by the project (project scripts call it for you)

Initial setup (one-time)
From the project root run the project's setup scripts (the project provides scripts that perform the steps below). Example commands you may use:

```bash
# Recommended top-level bootstrap (runs frontend deps install and backend sync)
pnpm setup
```

Manual equivalent (if not using the top-level script):
```bash
# 1) Install frontend deps
pnpm install

# 2) Sync Python environment (creates .venv at project root and installs Python deps)
uv sync
```

Notes:
- `uv sync` in this project creates `.venv` at the project root and installs Python dependencies described in `pyproject.toml`.
- After adding new Python dependencies or new modules, re-run the sync step to update `.venv`.

Activating the virtual environment
- macOS / Linux:
  ```bash
  source .venv/bin/activate
  ```
- Windows (PowerShell):
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
Once activated, `python` and `pip` will refer to the project's environment.

Installing or updating Python dependencies
- Prefer adding dependencies to `pyproject.toml` and let the project's sync script install them.
- If you need to install a package manually in a local dev flow:
  ```bash
  .venv/bin/python -m pip install <package>
  ```
- After changing `pyproject.toml` (or adding new backend modules), run:
  ```bash
  uv sync
  # or the project-provided helper:
  pnpm setup-backend
  ```

Regenerating TypeScript client (PyTauri)
- The project auto-generates a TypeScript client for frontend usage from Python handlers/models.
- After changing backend handlers or Pydantic models:
  1. Re-sync the Python environment:
     ```bash
     pnpm setup-backend
     # or
     uv sync
     ```
  2. Rebuild / run the Tauri dev flow that triggers client generation:
     ```bash
     pnpm tauri dev
     ```
- Do NOT manually edit files under `src/lib/client/` — they are auto-generated.

Running the backend for development
- You can run the backend as a standalone API server (useful for backend-only development / tests):
  ```bash
  # development mode with auto-reload
  uvicorn app:app --reload

  # or via the project's uv helper
  uv run python app.py
  ```
- Open the API docs at `http://localhost:8000/docs` (when running in FastAPI mode).

IDE configuration
- Point your IDE's Python interpreter to the project's `.venv` at the project root.
- Configure your editor to use the project's linters/formatters from the venv where applicable.
- Ensure path aliases (e.g., `@/*` → `src/`) used by the frontend are configured in your editor for TypeScript/JS.

CI / Build notes
- CI should:
  - Install Node dependencies
  - Run `uv sync` (or the project's backend setup) from the project root to install Python deps into `.venv`
  - Run `pnpm check-i18n`, `pnpm lint`, `pnpm test`, and other quality checks
  - When building Tauri desktop artifacts, ensure Rust toolchain is available on the CI runner
- Never commit secrets (API keys) to the repository. Use CI secrets / environment variables.

Common troubleshooting
- `.venv` not created / missing dependencies:
  - Make sure you're in the project root and run:
    ```bash
    uv sync
    ```
- Frontend type errors referencing generated client:
  - Regenerate the client after backend changes:
    ```bash
    pnpm setup-backend
    pnpm tauri dev
    ```
- Python version mismatch:
  - Use a Python version consistent with `pyproject.toml`; configure your toolchain (pyenv, system Python, etc.) accordingly.

Security & Privacy reminders
- Avoid persisting raw sensitive inputs unnecessarily. The project aims to store summaries/metadata where possible.
- Keep API keys and secrets in environment variables or CI secret stores, not in source.

Quick checklists
- New backend handler / model:
  - Add handler + Pydantic model
  - Import into `backend/handlers/__init__.py`
  - Run `pnpm setup-backend` (or `uv sync`)
  - Run `pnpm tauri dev` to regenerate TypeScript client, then update frontend usage
- New Python dependency:
  - Add to `pyproject.toml`
  - Run `uv sync`
  - Verify tests and frontend client (if models changed)

If you want, I can generate a short `docs/checklist.md` containing these checklists in an even more condensed form for PR reviewers and contributors.
