# Important Files — Rewind

This document lists the key files and directories you will use frequently when developing, testing, and maintaining Rewind. Use it as a quick reference to find where to make changes and where to look for the main pieces of the system.

## Docs (detailed workflows)
- `docs/getting_started.md` — Quick setup and common development commands (run/setup/use cases).
- `docs/architecture.md` — High-level architecture and design patterns (frontend / backend / agents).
- `docs/internationalization.md` — i18n workflow, file locations and validation commands.
- `docs/fastapi_usage.md` — (If present) instructions for running the backend as standalone FastAPI.

## Frontend
- `src/` — Main frontend app root (React + TypeScript).
- `src/views/` — Page-level components (route targets).
- `src/layouts/` — Layout wrappers (MainLayout, AuthLayout).
- `src/components/` — Reusable components organized by feature.
- `src/lib/config/menu.ts` — Menu configuration that drives routing and sidebar.
- `src/lib/stores/` — Zustand stores for global state (activity, agents, settings, ui).
- `src/lib/services/` — Service wrappers around the generated PyTauri client.
- `src/locales/en.ts` — English translations (source of truth for i18n).
- `src/locales/zh-CN.ts` — Chinese translations (mirror keys from `en.ts`).
- `src/lib/client/` — Auto-generated TypeScript client (DO NOT EDIT manually).

## Backend (Python / PyTauri)
- `backend/` (or `src-tauri/python/rewind_app/`) — Python backend modules exposed to Tauri.
- `backend/handlers/` — API handler modules. Add new handlers here and import them in `backend/handlers/__init__.py`.
- `backend/models/` — Pydantic models and request/response schemas.
- `app.py` — FastAPI application entrypoint for running backend standalone (dev/testing).
- `pyproject.toml` — Python project configuration and dependencies (at project root).

## Tauri / Rust bridge
- `src-tauri/src/lib.rs` — Rust ↔ Python bridge configuration (PyTauri/Tauri registration).
- `src-tauri/Cargo.toml` — Rust dependencies and Tauri configuration.

## Database & Persistence
- SQLite DB file(s) — location configured in backend (check config/env). Stores activities and related records.

## Config & Tooling
- `pnpm-workspace.yaml`, `package.json` — Frontend scripts, build and workspace config.
- `pnpm` scripts (package.json) — `dev`, `build`, `tauri dev`, `setup`, `setup-backend`, `bundle`, etc.
- `.env` / `.env.example` — Environment variables for local development (LLM keys, DB paths). Never commit secrets.

## Auto-generated / Do NOT edit
- `src/lib/client/` — Auto-generated PyTauri TypeScript client (regenerate via backend sync / tauri dev).
- `src/components/shadcn-ui/` — Generated shadcn/ui primitives (edit via shadcn CLI if applicable).
- `src/types/auto-imports.d.ts` — Auto-generated types.

## Tests & CI
- `tests/` — Unit and integration tests (if present).
- CI config (`.github/workflows/*`) — Build/test pipeline, ensure i18n and lint checks run here.

## Useful places to start editing
- Add a new page:
  1. `src/views/YourFeature/index.tsx`
  2. Add menu entry in `src/lib/config/menu.ts`
  3. Add route in `src/routes/Index.tsx`
  4. Create store under `src/lib/stores/` if needed
  5. Add service wrapper in `src/lib/services/`

- Add a backend handler:
  1. New handler in `backend/handlers/your_handler.py`
  2. Pydantic request model in `backend/models/`
  3. Import handler in `backend/handlers/__init__.py`
  4. Run `pnpm setup-backend` (or `uv sync`) and then `pnpm tauri dev` to regenerate the TypeScript client

## Notes & Best Practices
- Keep `src/lib/client/` auto-generated — do not edit.
- `src/locales/en.ts` is the source of truth for translation keys; always update it first.
- Python environment and `.venv` live at the project root — run `pnpm setup` or `uv sync` from the root.
- After changing Python handlers/models, re-sync backend and regenerate TypeScript client before using in frontend.
- Protect secrets: put API keys and credentials in environment variables; do not commit them.

If you want, I can create a short checklist file (docs/checklist.md) with the exact commands to run after common changes (new handler, new model, new translation keys, etc.).
