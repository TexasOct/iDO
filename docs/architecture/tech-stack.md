# Technology Stack

This document explains the technology choices behind iDO and the rationale for each decision.

## Overview

```
┌─────────────────────────────────────────────────┐
│           Frontend Technologies                 │
├─────────────────────────────────────────────────┤
│ React 19 + TypeScript 5 + Vite 6               │
│ Tailwind CSS 4 + shadcn/ui                     │
│ Zustand 5 + React Router                       │
│ i18next + React Hook Form + Zod               │
└─────────────────────────────────────────────────┘
                     ↕
          PyTauri Bridge (IPC)
                     ↕
┌─────────────────────────────────────────────────┐
│           Backend Technologies                  │
├─────────────────────────────────────────────────┤
│ Python 3.14+ + PyTauri 0.8                     │
│ FastAPI + Pydantic + asyncio                   │
│ pynput + mss + PIL + OpenCV                    │
│ SQLite + OpenAI API                            │
└─────────────────────────────────────────────────┘
                     ↕
┌─────────────────────────────────────────────────┐
│           Desktop Runtime                       │
├─────────────────────────────────────────────────┤
│ Tauri 2.x (Rust)                               │
│ Platform APIs (macOS, Windows, Linux)         │
└─────────────────────────────────────────────────┘
```

## Frontend Stack

### React 19
**Why**: Modern, component-based UI framework

**Key Features**:
- React Compiler for automatic optimization
- Improved server components (future)
- Concurrent rendering
- Mature ecosystem

**Alternatives Considered**:
- Vue 3: Less TypeScript integration
- Svelte: Smaller community, fewer libraries
- Solid: Too new, limited resources

### TypeScript 5
**Why**: Type safety prevents bugs

**Benefits**:
- Compile-time error detection
- Better IDE autocomplete
- Self-documenting code
- Refactoring confidence

**Configuration**:
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

### Vite 6
**Why**: Fast build tool

**Benefits**:
- Instant HMR (< 50ms)
- Native ES modules
- Optimized production builds
- Plugin ecosystem

**vs Webpack**:
- 10-100x faster dev server
- Simpler configuration
- Better DX

### Tailwind CSS 4
**Why**: Utility-first styling

**Benefits**:
- Rapid development
- Consistent design system
- Automatic purging (small bundles)
- No CSS-in-JS runtime cost

**Configuration**:
- Custom design tokens in `tailwind.config.js`
- Auto-sorting with `prettier-plugin-tailwindcss`
- Dark mode support

### Zustand 5
**Why**: Simple state management

**vs Redux**:
- No boilerplate
- Smaller bundle (1KB vs 8KB)
- Easier to learn
- Better TypeScript support

**vs Context API**:
- No provider hell
- Better performance (selective re-renders)
- DevTools integration

**Example**:
```typescript
const useActivityStore = create<ActivityState>((set) => ({
  activities: [],
  fetchActivities: async () => {
    const data = await apiClient.getActivities()
    set({ activities: data })
  }
}))
```

### shadcn/ui
**Why**: Accessible, customizable components

**Benefits**:
- Copy-paste components (not npm dependency)
- Full control over code
- Radix UI primitives (accessible)
- Tailwind-based styling

## Backend Stack

### Python 3.14+
**Why**: Ideal for AI/ML integration

**Benefits**:
- Rich LLM ecosystem (OpenAI, LangChain)
- Easy system integration (pynput, mss)
- Fast prototyping
- Strong typing with Pydantic

**Type Checking**:
```bash
uv run ty check  # Uses basedpyright
```

### PyTauri 0.8
**Why**: Python ↔ Rust bridge

**Benefits**:
- Write backend in Python
- Auto-generate TypeScript clients
- Shared handlers for desktop + web (FastAPI)
- Type-safe IPC

**Example**:
```python
@api_handler(body=MyRequest)
async def my_handler(body: MyRequest) -> dict:
    # Available in PyTauri AND FastAPI
    return {"result": "..."}
```

**Auto-generates**:
```typescript
// src/lib/client/
export async function myHandler(body: MyRequest): Promise<MyResponse>
```

### FastAPI
**Why**: Modern async web framework

**Benefits**:
- Automatic OpenAPI docs
- Pydantic validation
- High performance (ASGI)
- Easy testing

**Development**:
```bash
uvicorn app:app --reload
# Visit http://localhost:8000/docs
```

**Same handlers work in**:
- Desktop app (PyTauri)
- Web API (FastAPI)
- No code duplication

### Pydantic
**Why**: Data validation and serialization

**Benefits**:
- Runtime type validation
- Auto snake_case ↔ camelCase conversion
- JSON schema generation
- Clear error messages

**Example**:
```python
class Activity(BaseModel):
    activity_id: str  # Python: snake_case
    start_time: datetime
    
# Auto-converts to/from:
# {activityId: "...", startTime: "..."}  // TypeScript
```

### SQLite
**Why**: Embedded database

**Benefits**:
- No server setup
- ACID transactions
- Fast for < 100GB
- Single file backup

**vs PostgreSQL**:
- Simpler deployment
- Lower resource usage
- Perfect for local-first apps

**vs JSON files**:
- Structured queries
- Indexing support
- Concurrent access

### pynput
**Why**: Cross-platform input monitoring

**Benefits**:
- Works on macOS, Windows, Linux
- Simple API
- Keyboard + mouse support

**Platform Support**:
- macOS: CoreGraphics
- Windows: Windows API hooks
- Linux: X11/Wayland

### mss (Multiple Screen Shots)
**Why**: Fast screenshot capture

**Benefits**:
- 30-100 fps capture speed
- Multi-monitor support
- Low CPU usage
- Cross-platform

**vs PIL.ImageGrab**:
- 5-10x faster
- Better multi-monitor support

### OpenCV + PIL
**Why**: Image processing

**Uses**:
- Perceptual hashing (duplicate detection)
- Image resizing/compression
- Region cropping
- Text detection (experimental)

## Desktop Runtime

### Tauri 2.x
**Why**: Modern desktop framework

**vs Electron**:
- 10x smaller bundle (3MB vs 130MB)
- Lower memory usage (system WebView)
- Better security (no Node.js in renderer)
- Rust reliability

**Benefits**:
- Fast performance
- Native system integration
- Small bundle size
- Active development

**Architecture**:
```
Rust Core (Tauri)
    ↓
PyTauri Bridge
    ↓
Python Backend
    ↓
FastAPI (development only)
```

## Development Tools

### Package Managers

**Frontend**: pnpm
- Faster than npm (parallel installs)
- Disk space efficient (shared cache)
- Strict dependencies

**Backend**: uv
- Fast Python package installer
- Drop-in pip replacement
- Lock file support

### Type Checking

**TypeScript**:
```bash
pnpm tsc --noEmit
```

**Python**:
```bash
uv run ty check  # basedpyright
```

### Code Formatting

**All languages**:
```bash
pnpm format  # Prettier + Black
```

### Linting

```bash
pnpm lint  # ESLint + Ruff
```

## Infrastructure

### Build System
- **Frontend**: Vite (ES modules)
- **Backend**: uv (Python packages)
- **Desktop**: Cargo (Rust)

### CI/CD
- GitHub Actions
- Automated tests on push
- Cross-platform builds

### Monitoring
- Local logs (`~/.config/ido/logs/`)
- Error tracking (future: Sentry)

## Performance Characteristics

| Component | Bundle Size | Memory Usage | Startup Time |
|-----------|-------------|--------------|--------------|
| Frontend (React) | ~500KB gzipped | ~50MB | < 1s |
| Backend (Python) | ~20MB | ~100MB | ~2s |
| Tauri Runtime | ~3MB | ~30MB | < 0.5s |
| **Total** | **~23.5MB** | **~180MB** | **~3.5s** |

**vs Electron Equivalent**:
- Bundle: 130MB+ (5.5x larger)
- Memory: 300MB+ (1.7x more)
- Startup: 5-10s (2-3x slower)

## Future Considerations

### Potential Additions
- **Rust backend**: For performance-critical processing
- **WebAssembly**: For client-side LLM inference
- **Edge Functions**: For optional cloud features
- **Mobile support**: React Native or Flutter

### Technology Watch
- **React Server Components**: When Tauri supports
- **Bun**: Alternative to Node.js (faster)
- **Mojo**: Python replacement for performance

## Decision Matrix

### When to Use Each Tool

| Task | Tool | Why |
|------|------|-----|
| UI Component | React + TypeScript | Type safety, reusability |
| State Management | Zustand | Simplicity, performance |
| Styling | Tailwind | Rapid development, consistency |
| API Handler | @api_handler | Works in PyTauri + FastAPI |
| Data Validation | Pydantic | Runtime safety, auto-conversion |
| Database | SQLite | Local-first, simple |
| Build Tool | Vite | Speed, DX |
| Desktop Runtime | Tauri | Size, performance |

## Next Steps

- 🏗️ [Three-Layer Design](./three-layer-design.md) - Architecture overview
- 🔄 [Data Flow](./data-flow.md) - How data moves through the system
- 💻 [Frontend Guide](../guides/frontend/README.md) - Use frontend stack
- 🐍 [Backend Guide](../guides/backend/README.md) - Use backend stack
