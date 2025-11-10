# iDO

> Local-first AI desktop copilot that captures your activity stream, summarizes context with LLMs, and recommends the next task without sending data to the cloud.

---

## Why iDO
- **Three-layer pipeline** (Perception → Processing → Consumption) keeps keyboard, mouse, and screenshot data on device.
- **Shared API surface**: PyTauri + FastAPI handlers auto-generate a type-safe TypeScript client.
- **Modern frontend**: React 19 + Vite 6 + Zustand 5 + Tailwind CSS 4 for a responsive timeline UI.
- **SQLite persistence** with friendly stores for activities, models, permissions, and settings.
- **Pluggable agents & models** so you can bring your own LLM and automate custom workflows.

---

## Architecture at a Glance
```
Perception  →  Processing  →  Consumption
raw records    LLM summaries   recommendations & UI
```
- **Perception layer** collects keyboard, mouse, and screen events (~20 s windows).
- **Processing layer** filters noise, summarizes with the active LLM, and writes Activities/Tasks to SQLite.
- **Consumption layer** drives the Tauri UI and emits desktop notifications via the event bus.

---

## Screenshots (replace with real captures)

![Dashboard screenshot placeholder](docs/images/dashboard-placeholder.png)
_Replace with an actual dashboard screenshot showing the timeline, active tasks, and model selector._

![Permissions flow placeholder](docs/images/permissions-placeholder.png)
_Replace with macOS permission prompts + the in-app helper panel._

---

## Getting Started

### Prerequisites
- Node.js ≥ 20 & `pnpm` ≥ 9
- Rust toolchain (for Tauri 2.x) and `cargo`
- Python ≥ 3.14 with [`uv`](https://github.com/astral-sh/uv)
- macOS accessibility + screen recording permissions if you plan to capture activity

### Install everything
```bash
pnpm setup            # installs frontend deps + syncs backend (uv)
```

### Development workflows
- **Full desktop app with live TS client generation**
  ```bash
  pnpm tauri:dev:gen-ts
  ```
- **Frontend only (Vite @ http://localhost:5173)**
  ```bash
  pnpm dev
  ```
- **Backend API server (FastAPI + auto handlers)**
  ```bash
  uvicorn app:app --reload
  ```
- **PyTauri CLI entry point**
  ```bash
  uv run python backend/cli.py --help
  ```

### Quality & production commands
- `pnpm format` / `pnpm lint` – Prettier formatting & check
- `pnpm tsc` – TypeScript compile check (required before PRs touching frontend)
- `pnpm check-i18n` – Ensure locale keys stay in sync
- `uv run ty check` – Python typing (required before PRs touching backend)
- `pnpm tauri build` – Production desktop bundle
- `pnpm tauri:build:signed` – macOS signed artifact (requires certificates)

---

## Project Structure
```
.
├── backend/           # Python perception, processing, handlers, agents
├── src/               # React UI, components, stores, hooks, locales
├── src-tauri/         # Tauri Rust runner + PyTauri bridge (see python/ido_app)
├── docs/              # Architecture, dev guides, permissions references
└── scripts/           # Cross-platform tooling (setup, bundle, signing)
```

---

## Contributing
1. Fork & create a feature branch.
2. Run `pnpm setup` once, then follow the workflow above.
3. Keep type checks green (`pnpm tsc`, `uv run ty check`) and add tests when possible.
4. Submit a PR with screenshots (replace the placeholders!) and a short change summary.

Issues and discussions live at **https://github.com/TexasOct/iDO** – bug reports and feature ideas are always welcome!
