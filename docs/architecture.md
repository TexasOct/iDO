# Rewind — Architecture Guidelines

This document summarizes the high-level architecture, design principles, and key implementation patterns for Rewind. It's intended as a concise reference for contributors and maintainers.

---

## Purpose
Rewind is a desktop application that captures user activity (keyboard, mouse, screenshots), processes and summarizes it with LLMs, and surfaces insights and agent-driven recommendations. The architecture prioritizes modularity, privacy, testability, and gradual, real-time updates.

---

## High-level Layers
1. Perception
   - Captures raw inputs: keyboard, mouse, screenshots.
   - Short-lived buffers / sliding windows; minimal local preprocessing.
2. Processing
   - Filters, de-duplicates, and summarizes events.
   - LLM-based summarization + heuristics to merge related events into Activities.
   - Persists canonical Activity records to SQLite.
3. Consumption
   - UI for timeline, analytics, and agent tasks.
   - Agent system that proposes or executes tasks based on Activities.

---

## Frontend (React + TypeScript)
- Structure
  - Pages: `src/views/` (route targets)
  - Containers: `src/components/` (business logic/composition)
  - Components / Primitives: shared UI building blocks (shadcn/ui)
- Routing & Load
  - React Router with lazy-loaded routes for code-splitting.
- State
  - Global: Zustand stores in `src/lib/stores/` (selective subscriptions).
  - Local: component state + controlled forms (React Hook Form + Zod).
  - Persist important preferences with Zustand persistence.
- Services
  - A thin service layer wraps calls to the PyTauri-generated TypeScript client (`src/lib/client/`).
  - Services handle retries, logging, and mapping backend shapes → frontend types.
- Realtime
  - Use Tauri events for push updates (e.g., `activity-created`, `agent-task-update`).
  - Debounce events (300ms) and batch UI updates to avoid thrashing.
- i18n
  - TypeScript-first translations (`src/locales/en.ts` is source of truth).
  - `pnpm check-i18n` is used to validate translation consistency.
- UX Patterns
  - Defensive date parsing, optional chaining, and graceful empty/loading states.
  - Virtualization/virtual scrolling for long timelines.

---

## Backend (Python + PyTauri; optional FastAPI)
- Runtime
  - Primary: PyTauri integrated Python modules exposed via Rust bridge for desktop.
  - Optional: FastAPI server for standalone development/testing.
- Handler System
  - Universal `@api_handler` decorator registers functions for PyTauri and FastAPI.
  - Handlers with request bodies must accept a single Pydantic model parameter (PyTauri constraint).
- Data Flow
  - RawRecords (short buffer) → every ~10s processed → Events with `events_summary` → LLM summarization → Activity → persisted to SQLite → consumed by agents.
- Agents
  - AgentFactory pattern: register agents, each extends `BaseAgent` and implements `can_handle()` and `execute()`.
  - Task lifecycle: `todo` → `doing` → `done` / `cancelled`.
  - Support parallel execution where safe.
- Models
  - Pydantic models for request/response and DB mapping.
  - CamelCase ↔ snake_case conversion handled in the registry/client generation.
- Client generation
  - PyTauri auto-generates TypeScript client (`src/lib/client/`) from Python handlers — do not edit generated files.
  - After changing Python handlers/models, run backend sync (e.g., `pnpm setup-backend` / `uv sync`) and regenerate client.

---

## Data & Persistence
- SQLite for Activity storage; keep schemas stable and backward compatible.
- Activity model should always include: id, name, description, timestamp/startTime, endTime, eventSummaries (sourceEvents).
- Store minimal PII: persist only what is necessary for features; prefer hashes/metadata over raw sensitive content. Secure DB file on disk and document retention policies.

---

## Design Patterns & Best Practices
- Configuration-Driven UI: menu and routes driven from `src/lib/config/menu.ts`.
- Service Layer: centralizes error handling for calls to the backend client.
- Factory Pattern: for agent extensibility (AgentFactory).
- Selective Store Subscriptions: prefer `useStore(state => state.x)` to avoid re-renders.
- Event-Driven Updates: use Tauri events; debounce and batch updates.
- Defensive Parsing: always validate timestamps and fallback to `Date.now()`.

---

## Performance Considerations
- Batch LLM calls and use summarization caching to reduce cost and latency.
- Compress screenshots and use perceptual hashing for deduplication.
- Limit in-memory timeline blocks (e.g., keep most recent 100 date blocks).
- Use virtualization for long lists and memoization for pure components.

---

## Security & Privacy
- Monitor sensitive data: clearly document what is captured and where it's stored.
- Provide opt-out controls and clear indicators when capture is active.
- Secure storage (file permissions) and minimize retention by default.
- Sanitize and avoid sending raw screenshots or keystrokes externally unless explicitly configured by user and secured.

---

## Testing & Local Development
- FastAPI mode available for backend-only testing (`uvicorn app:app --reload`).
- Unit tests for:
  - Data mapping functions (db ↔ API ↔ frontend shapes).
  - Agent logic and state transitions.
  - Handler validation (Pydantic schemas).
- Integration tests should cover end-to-end data flow: capture → processing → activity → UI update.

---

## Release / Build Notes
- Frontend: build via `pnpm build`.
- Desktop: `pnpm tauri build` (CI: `pnpm tauri build --ci`).
- After Python model/handler changes:
  1. Re-sync Python env: `pnpm setup-backend` / `uv sync`.
  2. Regenerate TypeScript client by running the Tauri dev/build flow that triggers client generation.
- Do not edit `src/lib/client/` — it is auto-generated.

---

## Where to extend
- Add new UI pages under `src/views/` and register menu items in `src/lib/config/menu.ts`.
- Add new backend handlers under `backend/handlers/` with proper Pydantic models and import them in `backend/handlers/__init__.py`.
- Add agents by extending `BaseAgent` and registering with `AgentFactory`.

---

Keep this document focused and update it when core architecture or critical integration points change.
