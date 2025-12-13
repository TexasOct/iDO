# Architecture Overview

iDO is built on a **three-layer architecture** designed for privacy, extensibility, and intelligent task recommendations.

## Quick Links

- [Three-Layer Design](./three-layer-design.md) - Core architectural pattern
- [Data Flow](./data-flow.md) - How data moves through the system
- [Tech Stack](./tech-stack.md) - Technology choices and rationale

## System Overview

```
┌────────────────────────────────────────────────────────────┐
│                  iDO Desktop Application                   │
│                        (Tauri 2.x)                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Frontend (React 19 + TypeScript)            │   │
│  │  • Activity timeline visualization                  │   │
│  │  • Task management interface                        │   │
│  │  • Settings and configuration                       │   │
│  │  • Zustand state management                         │   │
│  └────────────────┬────────────────────────────────────┘   │
│                   │ PyTauri IPC                            │
│  ┌────────────────▼────────────────────────────────────┐   │
│  │         Backend (Python 3.14+)                      │   │
│  │  • Event capture and processing                     │   │
│  │  • LLM integration and analysis                     │   │
│  │  • Agent task system                                │   │
│  │  • SQLite persistence                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Three-Layer Architecture

iDO processes user activities through three distinct layers:

### 1. Perception Layer (Capture)

**Purpose**: Collect raw user activity data

- Monitors keyboard events (pynput)
- Tracks mouse interactions (pynput)
- Captures screenshots (mss, PIL)
- 20-second sliding window buffer
- Platform-specific implementations (macOS, Windows, Linux)

**Output**: `RawRecord` objects

### 2. Processing Layer (Analyze)

**Purpose**: Transform raw data into meaningful activities

**Two-step extraction with RawAgent**:

1. **RawAgent**: Extracts high-level scene descriptions from screenshots (images → text)
2. **ActionAgent**: Extracts actions from scene descriptions (text → actions)
3. **KnowledgeAgent**: Extracts knowledge from scene descriptions or actions (text → knowledge)
4. **EventAgent**: Aggregates actions into activities (every 10 minutes)

**Benefits**:

- Process images once, reuse text data multiple times
- 75% token reduction for downstream agents
- Better consistency (all agents work from same scene data)
- Memory-only scene descriptions (auto garbage-collected)

**Output**: `Activity` objects with AI-generated summaries

### 3. Consumption Layer (Recommend)

**Purpose**: Provide value to users

- Displays activity timeline
- Generates task recommendations via agents
- Provides search and analytics
- Real-time UI updates via Tauri events

**Output**: User interface and task recommendations

## Key Design Principles

### 1. Privacy-First

- ✅ All data processing happens locally
- ✅ No mandatory cloud uploads
- ✅ User controls LLM provider
- ✅ Open source and auditable

### 2. Extensibility

- ✅ Plugin-based agent system
- ✅ `@api_handler` decorator for easy API addition
- ✅ Modular perception layer
- ✅ Configurable processing pipeline

### 3. Type Safety

- ✅ TypeScript throughout frontend
- ✅ Pydantic models in backend
- ✅ Auto-generated TS client from Python
- ✅ Compile-time checks prevent runtime errors

### 4. Developer Experience

- ✅ Hot reload for frontend
- ✅ Auto API client generation
- ✅ Single handler works in PyTauri + FastAPI
- ✅ Comprehensive documentation

## Component Communication

### Frontend ↔ Backend

```typescript
// Frontend (TypeScript)
import { apiClient } from '@/lib/client'

const activities = await apiClient.getActivities({
  startDate: '2024-01-01',
  endDate: '2024-01-31'
})
```

```python
# Backend (Python)
@api_handler(body=GetActivitiesRequest)
async def get_activities(body: GetActivitiesRequest) -> dict:
    # Auto-registered in both PyTauri and FastAPI
    return {"activities": [...]}
```

### Event-Driven Updates

```python
# Backend emits event
from backend.core.events import emit_event

await emit_event('activity-created', {
    'id': activity.id,
    'timestamp': activity.timestamp
})
```

```typescript
// Frontend listens
import { useTauriEvents } from '@/hooks/useTauriEvents'

useTauriEvents({
  'activity-created': (payload) => {
    // Update UI immediately
    activityStore.addActivity(payload)
  }
})
```

## Data Flow Example

```
[User types in editor]
         ↓
  Keyboard Event (pynput)
         ↓
  RawRecord stored in 60s buffer
         ↓
  Every 30s: Processing triggered
         ↓
  Accumulate 20+ screenshots
         ↓
  RawAgent: Extract scene descriptions (images → text)
  └─> Scene: visual_summary, detected_text, application_context, etc.
         ↓
  ActionAgent: Extract actions from scenes (text-only, NO images)
  └─> Actions with scene_index references
         ↓
  KnowledgeAgent: Extract knowledge from scenes/actions (text-only)
  └─> Knowledge items
         ↓
  Save actions/knowledge to database
         ↓
  Emit 'action-created', 'knowledge-created' events
         ↓
  Every 10min: EventAgent aggregates actions → activities
         ↓
  Frontend incremental sync (every 30s)
         ↓
  User sees activities in timeline
```

## Technology Decisions

### Why PyTauri?

- Seamless Python ↔ Rust integration
- Shared codebase for desktop and web (FastAPI)
- Auto-generates TypeScript clients
- Better than Electron (smaller, faster)

### Why Zustand?

- Simpler than Redux
- TypeScript-first
- No boilerplate
- Built-in DevTools support

### Why SQLite?

- Local-first architecture
- No server setup required
- ACID transactions
- Fast for < 100GB data

### Why Tailwind CSS?

- Utility-first for rapid development
- Consistent design system
- Smaller bundle size than CSS-in-JS
- Auto-purging unused styles

## Performance Characteristics

| Aspect       | Strategy                                | Result            |
| ------------ | --------------------------------------- | ----------------- |
| **Frontend** | Code splitting, virtual scrolling       | Fast initial load |
| **Backend**  | Batch processing, LLM caching           | Low latency       |
| **Database** | Indexed queries, prepared statements    | Quick retrieval   |
| **Memory**   | 20s sliding window, image deduplication | Bounded usage     |
| **Network**  | Incremental updates, event debouncing   | Minimal overhead  |

## Extensibility Points

### 1. Add New Perception Source

```python
# Implement BaseCapture protocol
class MyCapture(BaseCapture):
    def start(self): ...
    def stop(self): ...
    def get_stats(self): ...
```

### 2. Add New Agent

```python
class MyAgent(BaseAgent):
    async def can_handle(self, activity: Activity) -> bool: ...
    async def execute(self, activity: Activity) -> Task: ...
```

### 3. Add New API Handler

```python
@api_handler(body=MyRequest)
async def my_handler(body: MyRequest) -> dict:
    return {"result": "..."}
```

### 4. Add New Frontend View

```typescript
// Create component in src/views/MyView/
// Add route in src/lib/config/menu.ts
```

## Next Steps

- 📖 [Three-Layer Design](./three-layer-design.md) - Deep dive into the architecture
- 🔄 [Data Flow](./data-flow.md) - Understand data transformations
- 🛠️ [Tech Stack](./tech-stack.md) - Learn about technology choices
- 💻 [Frontend Guide](../guides/frontend/README.md) - Frontend development
- 🐍 [Backend Guide](../guides/backend/README.md) - Backend development
