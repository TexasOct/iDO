# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rewind is a Tauri-based desktop application that monitors and analyzes user activity (keyboard, mouse, screenshots) using AI to provide intelligent insights and task recommendations. It features a three-layer architecture:

1. **Perception Layer** - Captures raw user input (keyboard, mouse, screenshots)
2. **Processing Layer** - Filters, summarizes, and organizes events using LLM
3. **Consumption Layer** - Provides intelligent analysis and agent-based task execution

## Technology Stack

### Frontend
- **Framework**: React 19 + TypeScript 5
- **Build Tool**: Vite 6
- **Routing**: React Router 7
- **State Management**: Zustand 5 (with persist middleware)
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Styling**: Tailwind CSS 4
- **Forms**: React Hook Form + Zod
- **Date Handling**: date-fns
- **Notifications**: Sonner

### Backend
- **Runtime**: Tauri 2.x (Rust)
- **Python Backend**: PyTauri 0.8 (Python ↔ Rust bridge)
- **Database**: SQLite
- **LLM Integration**: OpenAI API (configurable)
- **Image Processing**: OpenCV, PIL
- **System Monitoring**: pynput (keyboard/mouse), mss (screenshots)

## Development Commands

### Frontend Development

```bash
# Start development server (frontend only)
pnpm dev

# Build TypeScript and frontend
pnpm build

# Preview production build
pnpm preview

# Format code
pnpm format

# Check formatting (CI)
pnpm lint
```

### Tauri Development

```bash
# Start Tauri app in development mode (includes frontend + backend)
pnpm tauri dev

# Build production app
pnpm tauri build

# Generate PyTauri client bindings (after backend changes)
# This auto-generates TypeScript client code in src/client/
```

### Backend Development

Backend code is written in Python and integrated via PyTauri. Key points:

- Backend entry point: Python module exposed via `src-tauri/src/lib.rs`
- PyTauri automatically generates TypeScript client in `src/client/` (DO NOT manually edit)
- Communication: Frontend → PyTauri Client → Rust → Python

## Architecture Guidelines

### Frontend Architecture

**Component Hierarchy:**
```
Pages (src/views/)                    # Data fetching, state management
  ├─ Containers (src/components/)     # Business logic, composition
  │   └─ Components                   # Pure presentation
  │       └─ Primitives (shadcn-ui)   # Base UI components
```

**State Management Strategy:**
- **Zustand Stores** (`src/lib/stores/`) for cross-component state
  - `activity.ts` - Timeline data and filters
  - `agents.ts` - Agent tasks and execution state
  - `dashboard.ts` - Metrics and statistics
  - `settings.ts` - LLM configuration
  - `ui.ts` - UI state (sidebar, menu selection)
- **Props/Callbacks** for parent-child communication
- **Context** for theme and global configuration
- **Tauri Events** for backend → frontend real-time updates

**Routing Strategy:**
- React Router with lazy-loaded views for code splitting
- Menu configuration in `src/lib/config/menu.ts` drives both routing and sidebar
- UI state syncs with router location to maintain menu highlighting

**Communication Patterns:**
```
User Action → Component Handler → Zustand Action → Service Layer → PyTauri Client → Backend
                                                                                      ↓
Frontend Component ← Zustand Store Update ← Response/Tauri Event ←←←←←←←←←←←←←←←←←←←←←
```

### Backend Architecture

**Data Flow:**
```
Raw Records (滑动窗口 20s)
    ↓ 每10秒处理
Events (带 events_summary)
    ↓ LLM 总结 + 活动合并判断
Activity (持久化到 SQLite)
    ↓ 智能分析
Agent 任务推荐 → TODO
```

**Agent System:**
- Factory pattern for extensible agents (`AgentFactory`)
- Base class `BaseAgent` with `execute()` and `can_handle()` methods
- Tasks have states: `todo`, `doing`, `done`, `cancelled`
- Support parallel execution

**Data Models:**
- `RawRecord` - Raw input events (timestamp, type, data)
- `Event` - Filtered and summarized events
- `Activity` - Grouped related events with LLM-generated description
- `Task` - Agent tasks with execution state

### Key Design Patterns

1. **Configuration-Driven Menu**: Menu items defined in `src/lib/config/menu.ts`
   - Supports position grouping (main/bottom)
   - Badge notifications
   - Dynamic visibility control

2. **PyTauri Client Auto-Generation**:
   - Backend changes trigger automatic TypeScript client generation
   - Located in `src/client/` (marked as auto-generated)
   - Never manually edit client files

3. **Service Layer Pattern**:
   - Services in `src/lib/services/` wrap PyTauri client calls
   - Handles error logging and retry logic
   - Used by Zustand store actions

4. **Store Subscription Optimization**:
   ```typescript
   // ✅ Good: Selective subscription
   const tasks = useAgentsStore(state => state.tasks)

   // ❌ Bad: Subscribe to entire store
   const store = useAgentsStore()
   ```

5. **Real-Time Updates via Tauri Events**:
   ```typescript
   import { listen } from '@tauri-apps/api/event'

   useEffect(() => {
     const unlisten = listen('agent-task-update', (event) => {
       updateTaskStatus(event.payload)
     })
     return () => unlisten.then(fn => fn())
   }, [])
   ```

## File Structure Conventions

### Do Not Edit
- `src/client/` - Auto-generated PyTauri client code
- `src/components/shadcn-ui/` - Generated shadcn/ui components (edit via CLI)
- `src/types/auto-imports.d.ts` - Auto-generated types

### Key Directories
- `src/views/` - Page-level components (route targets)
- `src/layouts/` - Layout wrappers (MainLayout, AuthLayout)
- `src/lib/stores/` - Zustand state management
- `src/lib/services/` - API service layer (wraps PyTauri client)
- `src/lib/types/` - TypeScript type definitions
- `src/lib/config/` - Configuration files (menu, constants)
- `src/components/` - Reusable components organized by feature
- `src/hooks/` - Custom React hooks

### Naming Conventions
- **Components**: PascalCase (`ActivityTimeline`)
- **Hooks**: camelCase with `use` prefix (`useActivityStore`)
- **Types**: PascalCase (`Activity`, `AgentTask`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRY_COUNT`)

## Common Patterns

### Adding a New Page

1. Create view component in `src/views/NewFeature/index.tsx`
2. Add menu item to `src/lib/config/menu.ts`
3. Add route in `src/routes/Index.tsx` with lazy loading:
   ```typescript
   const NewFeatureView = lazy(() => import('@/views/NewFeature'))
   ```
4. Create store if needed in `src/lib/stores/newFeature.ts`
5. Create service layer in `src/lib/services/newFeature/index.ts`

### Working with PyTauri Backend

1. Implement Python backend function
2. Expose via PyTauri decorators
3. Run build to regenerate TypeScript client
4. Import and use in service layer:
   ```typescript
   import { apiClient } from '@/client/apiClient'
   export async function fetchData() {
     return await apiClient.methodName(params)
   }
   ```

### Adding a New Agent

1. Extend `BaseAgent` in Python backend
2. Implement `execute()` and `can_handle()` methods
3. Register in `AgentFactory`
4. Update `AgentType` enum in `src/lib/types/agents.ts`
5. Add UI configuration in Agents view

## Performance Considerations

- **Lazy Loading**: All route components use React.lazy
- **Virtual Scrolling**: Use for long lists (activity timeline)
- **Memoization**: Apply React.memo to pure presentational components
- **Store Subscriptions**: Always use selectors to minimize re-renders
- **Image Optimization**: Backend compresses screenshots and uses perceptual hashing for deduplication
- **Batch Processing**: Backend processes events every 10 seconds to reduce LLM calls

## Important Files

- `docs/frontend.md` - Comprehensive frontend architecture documentation
- `docs/backend.md` - Backend system design documentation
- `src/lib/config/menu.ts` - Menu configuration (affects routing and UI)
- `src/routes/Index.tsx` - Application routing definition
- `src-tauri/src/lib.rs` - Rust-Python bridge configuration
- `src-tauri/Cargo.toml` - Rust dependencies including PyTauri

## Special Notes

- **TypeScript Strict Mode**: Project uses strict TypeScript settings
- **Path Aliases**: Use `@/*` for imports from `src/`
- **Theme System**: next-themes provider for light/dark mode
- **Form Validation**: Use React Hook Form + Zod schema validation
- **Error Boundaries**: Wrap major sections for graceful error handling
- **No Auto-Imports Config**: Project does not use unplugin-auto-import despite dependency presence
