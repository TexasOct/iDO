# Development Workflow

This guide covers common development scenarios and workflows for contributing to iDO.

## Quick Reference

```bash
# Development
pnpm dev                    # Frontend only (fast iteration)
pnpm tauri:dev:gen-ts      # Full app with TS generation
uvicorn app:app --reload   # Backend API only

# Code Quality
pnpm format                # Auto-format code
pnpm lint                  # Check code quality
pnpm tsc                   # TypeScript type check
uv run ty check            # Python type check
pnpm check-i18n            # Validate translations

# Build
pnpm tauri build           # Production build
pnpm bundle                # Platform-specific bundle
pnpm clean                 # Clean build artifacts
```

## Common Development Scenarios

### Scenario 1: Frontend UI Changes

**Use Case**: Modifying React components, styling, or UI logic

```bash
# Start fast dev server
pnpm dev
```

**Workflow**:
1. Edit files in `src/views/` or `src/components/`
2. Browser auto-refreshes with changes
3. Check browser console for errors
4. Run `pnpm tsc` to verify type safety

**Tips**:
- Use browser DevTools for debugging
- Hot reload is instant (no backend recompilation)
- Perfect for rapid UI iteration

### Scenario 2: Adding a New API Handler

**Use Case**: Creating new backend endpoints

**Step 1**: Create the handler
```python
# backend/handlers/my_feature.py
from backend.handlers import api_handler
from backend.models.base import BaseModel

class MyRequest(BaseModel):
    user_input: str

@api_handler(
    body=MyRequest,
    method="POST",
    path="/api/my-feature",
    tags=["feature"]
)
async def my_feature_handler(body: MyRequest) -> dict:
    """Handle my feature request"""
    return {"success": True, "result": body.user_input}
```

**Step 2**: Register the handler
```python
# backend/handlers/__init__.py
from . import my_feature  # Add this import
```

**Step 3**: Sync and regenerate client
```bash
pnpm setup-backend
pnpm tauri:dev:gen-ts
```

**Step 4**: Use in frontend
```typescript
// src/views/MyView/index.tsx
import { apiClient } from '@/lib/client'

const result = await apiClient.myFeatureHandler({
  userInput: 'test'
})
```

**Auto-generated**:
- ✅ PyTauri command: `apiClient.myFeatureHandler()`
- ✅ FastAPI endpoint: `POST /api/my-feature`
- ✅ TypeScript types in `src/lib/client/`

See [API Handler Guide](../guides/backend/api-handlers.md) for details.

### Scenario 3: Working with State Management

**Use Case**: Adding new global state

**Step 1**: Define store
```typescript
// src/lib/stores/myFeature.ts
import { create } from 'zustand'

interface MyFeatureState {
  data: string[]
  loading: boolean
  
  fetchData: () => Promise<void>
  addItem: (item: string) => void
}

export const useMyFeatureStore = create<MyFeatureState>((set) => ({
  data: [],
  loading: false,
  
  fetchData: async () => {
    set({ loading: true })
    const result = await apiClient.getMyData()
    set({ data: result.data, loading: false })
  },
  
  addItem: (item) => set((state) => ({ 
    data: [...state.data, item] 
  }))
}))
```

**Step 2**: Use in components
```typescript
// src/views/MyView/index.tsx
const { data, loading, fetchData } = useMyFeatureStore()

useEffect(() => {
  fetchData()
}, [fetchData])
```

### Scenario 4: Adding Internationalization

**Use Case**: Supporting new languages or adding translations

**Step 1**: Add to English (source)
```typescript
// src/locales/en.ts
export const en = {
  myFeature: {
    title: 'My Feature',
    description: 'Feature description',
    actions: {
      save: 'Save',
      cancel: 'Cancel'
    }
  }
}
```

**Step 2**: Add corresponding translations
```typescript
// src/locales/zh-CN.ts
export const zhCN = {
  myFeature: {
    title: '我的功能',
    description: '功能描述',
    actions: {
      save: '保存',
      cancel: '取消'
    }
  }
}
```

**Step 3**: Validate
```bash
pnpm check-i18n
```

**Step 4**: Use in components
```typescript
import { useTranslation } from 'react-i18next'

const { t } = useTranslation()
return <h1>{t('myFeature.title')}</h1>
```

See [i18n Guide](../guides/features/i18n.md) for details.

### Scenario 5: Adding a New Agent

**Use Case**: Creating AI agents for task recommendations

**Step 1**: Create agent class
```python
# backend/agents/my_agent.py
from backend.agents.base import BaseAgent
from backend.models.activity import Activity
from backend.models.task import Task

class MyAgent(BaseAgent):
    """My custom agent"""
    
    async def can_handle(self, activity: Activity) -> bool:
        """Determine if this agent should process the activity"""
        return 'coding' in activity.description.lower()
    
    async def execute(self, activity: Activity) -> Task:
        """Generate task recommendation"""
        # Use LLM to analyze activity
        recommendation = await self._analyze_with_llm(activity)
        
        return Task(
            title=recommendation['title'],
            description=recommendation['description'],
            priority='high',
            source_activity_id=activity.id
        )
```

**Step 2**: Register agent
```python
# backend/agents/__init__.py
from .my_agent import MyAgent

AgentFactory.register(MyAgent())
```

See [Agent System Guide](../guides/backend/agents.md) for details.

### Scenario 6: Modifying Database Schema

**Use Case**: Adding new tables or columns

**Step 1**: Update schema
```python
# backend/core/sqls/schema.py
CREATE_MY_TABLE = """
CREATE TABLE IF NOT EXISTS my_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""
```

**Step 2**: Add queries
```python
# backend/core/sqls/queries.py
INSERT_MY_ITEM = """
INSERT INTO my_table (name) VALUES (?)
"""

SELECT_MY_ITEMS = """
SELECT * FROM my_table ORDER BY created_at DESC
"""
```

**Step 3**: Create repository
```python
# backend/core/db/my_repository.py
class MyRepository:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def add_item(self, name: str) -> int:
        with self.db._get_conn() as conn:
            cursor = conn.execute(queries.INSERT_MY_ITEM, (name,))
            return cursor.lastrowid
```

**Important**: All SQL must be in `queries.py` - never inline SQL in handlers.

### Scenario 7: Testing Backend Independently

**Use Case**: Debugging backend without running full Tauri app

```bash
# Start FastAPI server
uvicorn app:app --reload
```

Then visit http://localhost:8000/docs for interactive API documentation.

**Benefits**:
- ✅ Faster iteration (no Rust compilation)
- ✅ Auto-generated Swagger UI
- ✅ Test endpoints directly in browser
- ✅ Same handlers as PyTauri

## Code Quality Workflow

### Before Committing

Run these checks:

```bash
# 1. Format code
pnpm format

# 2. Check linting
pnpm lint

# 3. Verify TypeScript
pnpm tsc

# 4. Check Python types
uv run ty check

# 5. Validate i18n
pnpm check-i18n
```

### Pre-commit Checklist

- [ ] Code formatted with Prettier (`pnpm format`)
- [ ] No linting errors (`pnpm lint`)
- [ ] TypeScript compiles (`pnpm tsc`)
- [ ] Python types pass (`uv run ty check`)
- [ ] i18n keys consistent (`pnpm check-i18n`)
- [ ] Tests pass (if applicable)
- [ ] Clear commit message

## Debugging Tips

### Frontend Debugging

**Browser DevTools**:
```typescript
// Add breakpoints
debugger

// Log state
console.log('Store state:', useMyStore.getState())

// React DevTools profiling
```

**Zustand DevTools**:
```typescript
import { devtools } from 'zustand/middleware'

export const useMyStore = create(
  devtools((set) => ({ /* ... */ }))
)
```

### Backend Debugging

**Add logging**:
```python
import logging

logger = logging.getLogger(__name__)

@api_handler()
async def my_handler(body: Request):
    logger.debug(f"Request: {body}")
    result = process(body)
    logger.debug(f"Result: {result}")
    return result
```

**Check logs**:
```bash
tail -f ~/.config/ido/logs/app.log
```

### Common Issues

**TypeScript client not updating**:
```bash
pnpm setup-backend
pnpm tauri:dev:gen-ts
```

**Backend changes not reflected**:
```bash
# Restart Tauri app
# Or use FastAPI for hot reload
uvicorn app:app --reload
```

**i18n keys mismatch**:
```bash
pnpm check-i18n
# Fix reported missing keys
```

**Build failures**:
```bash
pnpm clean
pnpm setup
pnpm tauri build
```

## Performance Tips

### Frontend Optimization

```typescript
// Use React.memo for expensive components
export const MyComponent = React.memo(({ data }) => {
  // component logic
})

// Use Zustand selectors
const name = useStore((state) => state.user.name) // Only re-renders when name changes

// Lazy load routes
const MyView = lazy(() => import('./views/MyView'))
```

### Backend Optimization

```python
# Batch database operations
with db._get_conn() as conn:
    conn.executemany(query, data_list)

# Cache LLM results
@lru_cache(maxsize=100)
def process_activity(activity_id: str):
    # expensive LLM call
```

## Next Steps

- 📖 [Frontend Guide](../guides/frontend/README.md) - Deep dive into React architecture
- 🐍 [Backend Guide](../guides/backend/README.md) - Learn backend patterns
- 🏗️ [Architecture](../architecture/README.md) - Understand system design
- 🚀 [Building and Deployment](../deployment/building.md) - Create production builds

## Need Help?

- 📚 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/TexasOct/iDO/issues)
- 💬 [Ask Questions](https://github.com/TexasOct/iDO/discussions)
