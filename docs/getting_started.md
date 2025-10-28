# Getting Started

This document describes the minimal steps to set up a development environment for Rewind and the most common development commands.

> Key point: the Python environment lives at the **project root** (where `pyproject.toml` is). The `.venv` created by the setup commands will be placed at the project root.

---

## Prerequisites

- Node.js (LTS recommended)
- pnpm (package manager)
- Python 3.10+ (or the version specified in `pyproject.toml`)
- Rust toolchain (for Tauri)
- `uv` (uvtool) or `python -m venv` / your preferred Python virtualenv tooling
- (Optional) `uvicorn` for running the FastAPI server in development

---

## Initial setup (one-time)

From the project root:

1. Install frontend dependencies and perform project bootstrap:
   ```bash
   pnpm setup
   ```
   - On Windows:
   ```bash
   pnpm setup:win
   ```

2. Manual alternative (if not using `pnpm setup`):
   ```bash
   pnpm install
   uv sync         # this creates .venv at project root and installs Python deps (project's Python environment)
   pnpm check-i18n
   ```

3. After adding or changing Python modules/deps, re-sync Python env and regenerate TypeScript client:
   ```bash
   pnpm setup-backend   # runs uv sync and other sync steps
   # or
   uv sync
   # then
   pnpm tauri dev      # regenerates py-tauri client when needed
   ```

---

## Development workflows

### Frontend (fast iteration)
Run frontend dev server only:
```bash
pnpm dev
```
Build the frontend for production:
```bash
pnpm build
pnpm preview
```
Formatting / lint:
```bash
pnpm format
pnpm lint
pnpm check-i18n
```

### Backend (Python) — standalone FastAPI (optional)
Run the backend as a standalone FastAPI app for testing without Tauri:
```bash
# development with auto-reload
uvicorn app:app --reload
# or using provided helper
uv run python app.py
```
Open API docs at: `http://localhost:8000/docs`

### Full Tauri app (frontend + backend)
Run the full desktop app (development):
```bash
pnpm tauri dev
```
Build production desktop artifacts:
```bash
pnpm tauri build
# CI build (rebuild without launching)
pnpm tauri build --ci
```

---

## When to regenerate the TypeScript client

The PyTauri system auto-generates a TypeScript client under `src/lib/client/`. Whenever you:

- Add or change Python API handlers (in `backend/handlers/`)
- Add request/response Pydantic models

You must re-sync and rebuild to regenerate the client:
```bash
pnpm setup-backend
pnpm tauri dev   # or run the client generation step your workflow provides
```
Do NOT edit files inside `src/lib/client/` — they are auto-generated.

---

## Useful maintenance commands

- Rebuild distribution bundles:
  ```bash
  pnpm bundle        # macOS / Linux
  pnpm bundle:win    # Windows
  ```
- Clean build artifacts:
  ```bash
  pnpm clean
  ```

---

## Quick troubleshooting

- Python packages missing / `.venv` not created:
  - Ensure you're in the project root and run:
    ```bash
    uv sync
    ```
- TypeScript client out-of-date after Python changes:
  - Run:
    ```bash
    pnpm setup-backend
    pnpm tauri dev
    ```
- Tauri/Rust build issues:
  - Ensure Rust toolchain is installed and up-to-date (`rustup update`).
  - Check `src-tauri/Cargo.toml` and run `pnpm tauri build` to see full build output.

---

## Where to go next

- For detailed frontend architecture and coding patterns: `docs/frontend.md`
- For backend design and handler patterns: `docs/backend.md`
- For FastAPI usage (standalone development): `docs/fastapi_usage.md`
- For translations/i18n workflows: `docs/i18n.md`

(If any of the `docs/` files are missing, create them and document the relevant deeper workflows.)
