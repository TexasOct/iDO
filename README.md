# Rewind

Open-source desktop app that privately monitors and analyzes your activity to recommend tasks with AI. Built on a three-layer architecture (Perception → Processing → Consumption) and runs locally for privacy.

[简体中文](./README.zh-CN.md)

Badges: Python 3.14+, TypeScript 5, Tauri 2.x

---

## Highlights

- Privacy-first: all processing happens locally; no cloud upload
- Perception: keyboard, mouse, and smart screenshots (20s sliding window)
- Processing: event filtering, LLM summaries, activity merging, SQLite storage
- Agents: activity-aware task suggestions with extensible agent system
- Modern UI/UX: React 19, TypeScript 5, Tailwind CSS 4, i18n, light/dark theme

---

## Architecture

Three-layer design enables efficient data flow and real-time processing:

```
+------------------------------------------+
|   Consumption Layer                      |
|   AI analysis -> Task recommendations    |
|   frontend views, agents                 |
+------------------------------------------+
              ^
+------------------------------------------+
|   Processing Layer                       |
|   Event filtering -> LLM summary ->      |
|   Activity merging -> DB persistence     |
|   backend/processing, backend/llm        |
+------------------------------------------+
              ^
+------------------------------------------+
|   Perception Layer                       |
|   Keyboard -> Mouse -> Screenshots       |
|   backend/perception                     |
+------------------------------------------+
```

Tech stack
- Frontend: React 19, TypeScript 5, Vite 6, Tailwind 4
- Desktop: Tauri 2.x (Rust) with PyTauri 0.8
- Backend: Python 3.14+, FastAPI (for development)
- DB: SQLite (local)
- State: Zustand 5

---

## Quick Start

Requirements
- macOS / Linux / Windows
- Node.js ≥ 20, Rust (stable), Python ≥ 3.14, uv

Setup
```bash
git clone https://github.com/TexasOct/Rewind.git
cd Rewind

# macOS / Linux
pnpm setup

# Windows
pnpm setup:win

# Or install separately
pnpm setup-all
```

Development
```bash
# Frontend only
pnpm dev   # http://localhost:5173

# Full app with auto-generated TS client (recommended)
pnpm tauri:dev:gen-ts       # macOS/Linux
pnpm tauri:dev:gen-ts:win   # Windows

# Basic Tauri dev (no TS generation)
pnpm tauri dev

# Backend API only (FastAPI)
uvicorn app:app --reload
# or
uv run python app.py
```

Other commands
```bash
pnpm format        # format code
pnpm lint          # check formatting
pnpm check-i18n    # validate i18n keys
pnpm tauri build   # production build
pnpm clean         # clean artifacts
```

---

## Project Structure

```
rewind/
├─ src/                      # React frontend
│  ├─ views/                 # Pages (Dashboard, Chat, Agents, ...)
│  ├─ components/            # Reusable UI components
│  ├─ lib/
│  │  ├─ stores/             # Zustand state
│  │  ├─ client/             # Auto-generated PyTauri client
│  │  ├─ types/              # TS types
│  │  └─ config/             # Frontend config (routes, menus)
│  ├─ hooks/                 # Custom hooks (useTauriEvents, ...)
│  └─ locales/               # i18n files
├─ backend/                  # Python backend (source of truth)
│  ├─ handlers/              # API handlers (@api_handler)
│  ├─ core/                  # Coordinator, DB, events
│  ├─ models/                # Pydantic models
│  ├─ processing/            # Processing pipeline
│  ├─ perception/            # Keyboard, mouse, screenshots
│  ├─ agents/                # Task agents
│  └─ llm/                   # LLM integration
├─ src-tauri/                # Tauri app
│  ├─ python/rewind_app/     # PyTauri entry point
│  ├─ src/                   # Rust
│  └─ tauri.conf.json        # Config
├─ scripts/                  # Dev/build scripts
└─ docs/                     # Documentation
```

---

## Data Flow

```
RawRecords (20s window)
  -> Events (filtered + LLM summaries)
  -> Activities (aggregated)
  -> Tasks (agent recommendations)
  -> SQLite (persistence)
```

Key properties
- Local-only processing, no upload
- Incremental updates to avoid duplication
- Perceptual hash dedup for screenshots
- Real-time UI via Tauri events

---

## Documentation

- docs/development.md – environment, setup, FAQs
- docs/backend.md – backend architecture, models, agents
- docs/frontend.md – components, state, data flow
- docs/i18n.md – localization setup and checks
- docs/fastapi_usage.md – developing with FastAPI
- docs/python_environment.md – PyTauri integration and env

---

## Common Scenarios

- Frontend only: `pnpm dev`
- Frontend + Backend: `pnpm tauri:dev:gen-ts`
- Add Python handler: create in `backend/handlers`, import in `backend/handlers/__init__.py`, then `pnpm setup-backend`
- Debug backend only: `uvicorn app:app --reload` -> open http://localhost:8000/docs

---

## Universal API Handlers

Write once, use in both PyTauri and FastAPI with `@api_handler`.

```python
from backend.handlers import api_handler
from backend.models.base import BaseModel

class MyRequest(BaseModel):
    user_input: str

@api_handler(body=MyRequest, method="POST", path="/my-endpoint", tags=["my-module"])
async def my_handler(body: MyRequest) -> dict:
    return {"success": True, "data": body.user_input}
```

Frontend usage with auto-generated client:

```ts
import { apiClient } from '@/lib/client'
await apiClient.myHandler({ userInput: 'value' })
```

---

## Internationalization

Languages
- zh-CN, en

Add translations
1) Add keys to `src/locales/en.ts`
2) Add corresponding keys to `src/locales/zh-CN.ts`
3) Run `pnpm check-i18n`

---

## Privacy & Security

- Local-first design, user-controlled API keys for LLM
- Local SQLite storage; screenshots auto-expire
- Open source and auditable

---

## Contributing

- Use `pnpm format`, `pnpm lint`, and `pnpm check-i18n`
- Prefer precise typing (Pydantic models, strict TS)
- Clear PR descriptions; add docs for new features

Roadmap (short)
- Local GPU LLM support
- Optional cloud sync
- Browser extension, mobile app
- Activity classification with deep learning
- Team collaboration, more languages

---

## Acknowledgements

- Tauri, React, shadcn/ui, PyTauri
