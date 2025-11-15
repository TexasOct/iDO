# Backend Development Guide

This guide covers backend development for iDO, including API handlers, perception layer, processing pipeline, and agents.

## Quick Links

- [API Handlers](./api-handlers.md) - Create unified PyTauri + FastAPI endpoints
- [Perception Layer](./perception-layer.md) - Capture keyboard, mouse, screenshots
- [Processing Layer](./processing-layer.md) - Transform events into activities
- [Agents](./agents.md) - Build AI task recommendation agents

## Technology Stack

- **Python 3.14+** - Backend language
- **PyTauri 0.8** - Python ↔ Rust bridge
- **FastAPI** - Web framework (development)
- **Pydantic** - Data validation
- **SQLite** - Local database
- **OpenAI API** - LLM integration

## Project Structure

```
backend/
├── handlers/          # API handlers (@api_handler)
│   ├── __init__.py   # Handler registry
│   ├── activity.py
│   ├── agents.py
│   └── settings.py
│
├── models/            # Pydantic data models
│   ├── base.py       # BaseModel with camelCase conversion
│   ├── activity.py
│   └── task.py
│
├── core/              # Core systems
│   ├── coordinator.py  # System orchestration
│   ├── events.py      # Tauri event emission
│   ├── db/            # Database repositories
│   └── sqls/          # SQL schemas and queries
│
├── perception/        # Perception layer
│   ├── manager.py     # Perception coordinator
│   ├── keyboard.py
│   ├── mouse.py
│   └── screenshot_capture.py
│
├── processing/        # Processing layer
│   ├── pipeline.py    # Processing coordinator
│   ├── event_extractor.py
│   └── activity_merger.py
│
├── agents/            # AI agents
│   ├── base.py        # BaseAgent protocol
│   └── coding_agent.py
│
├── llm/               # LLM integration
│   └── client.py
│
└── config/            # Configuration
    ├── config.toml
    └── prompts_en.toml
```

## Development Workflow

### Starting Development

```bash
# Full Tauri app
pnpm tauri:dev:gen-ts

# Backend API only (faster iteration)
uvicorn app:app --reload
# Visit http://localhost:8000/docs
```

### Creating a New API Handler

**Step 1**: Define the handler

```python
# backend/handlers/my_feature.py
from backend.handlers import api_handler
from backend.models.base import BaseModel

class MyRequest(BaseModel):
    user_input: str  # snake_case in Python
    max_results: int = 10

class MyResponse(BaseModel):
    results: list[str]
    total_count: int

@api_handler(
    body=MyRequest,
    method="POST",
    path="/api/my-feature",
    tags=["features"]
)
async def my_feature_handler(body: MyRequest) -> MyResponse:
    """Handle my feature request"""
    # Process request
    results = process_data(body.user_input, body.max_results)
    
    return MyResponse(
        results=results,
        total_count=len(results)
    )
```

**Step 2**: Register the handler

```python
# backend/handlers/__init__.py
from . import my_feature  # Import the module
```

**Step 3**: Sync backend

```bash
pnpm setup-backend
```

**Step 4**: Use in frontend (auto-generated)

```typescript
import { apiClient } from '@/lib/client'

const result = await apiClient.myFeatureHandler({
  userInput: 'test',  // camelCase in TypeScript
  maxResults: 10
})

console.log(result.totalCount)  // Auto-converted from snake_case
```

## Core Concepts

### API Handler System

The `@api_handler` decorator makes your function available in both:
- **PyTauri** (desktop app)
- **FastAPI** (web API for development)

```python
@api_handler(body=RequestModel)
async def handler(body: RequestModel) -> ResponseModel:
    return ResponseModel(...)

# Automatically creates:
# - PyTauri command: handler()
# - FastAPI endpoint: POST /api/handler
# - TypeScript client: apiClient.handler()
```

See [API Handlers Guide](./api-handlers.md) for details.

### Data Models

All models inherit from `BaseModel` for automatic camelCase conversion:

```python
from backend.models.base import BaseModel

class Activity(BaseModel):
    activity_id: str          # Python: snake_case
    start_time: datetime
    end_time: datetime
    description: str

# Auto-converts to/from TypeScript:
# { activityId: string, startTime: Date, endTime: Date, description: string }
```

### Database Operations

**All SQL queries must be in `backend/core/sqls/queries.py`**:

```python
# backend/core/sqls/queries.py
SELECT_ACTIVITIES_BY_DATE = """
    SELECT * FROM activities
    WHERE DATE(start_time) >= ? AND DATE(end_time) <= ?
    ORDER BY start_time DESC
"""

# backend/core/db/activity_repository.py
class ActivityRepository:
    def get_by_date_range(self, start: str, end: str) -> list[Activity]:
        with self.db._get_conn() as conn:
            cursor = conn.execute(queries.SELECT_ACTIVITIES_BY_DATE, (start, end))
            return [Activity(**row) for row in cursor.fetchall()]
```

### Event Emission

Backend can emit events to frontend:

```python
from backend.core.events import emit_event

# Emit event
await emit_event('activity-created', {
    'id': activity.id,
    'title': activity.title,
    'timestamp': activity.start_time.isoformat()
})
```

```typescript
// Frontend receives
useTauriEvents({
  'activity-created': (payload) => {
    console.log('New activity:', payload)
  }
})
```

## Common Patterns

### Async Database Operations

```python
@api_handler(body=GetActivitiesRequest)
async def get_activities(body: GetActivitiesRequest) -> dict:
    # Run blocking DB operation in thread pool
    def _query():
        db = get_db_manager()
        return db.get_activities(body.start_date, body.end_date)
    
    activities = await asyncio.to_thread(_query)
    return {"activities": activities}
```

### Error Handling

```python
from backend.core.logger import logger

@api_handler(body=MyRequest)
async def my_handler(body: MyRequest) -> dict:
    try:
        result = await process(body)
        return {"success": True, "result": result}
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"success": False, "error": "Internal error"}
```

### LLM Integration

```python
from backend.llm.client import get_llm_client

async def summarize_activity(screenshots: list[str]) -> str:
    client = get_llm_client()
    
    prompt = build_prompt(screenshots)
    response = await client.call(
        prompt=prompt,
        max_tokens=1000,
        temperature=0.7
    )
    
    return response['summary']
```

## Perception Layer

Monitor user activity:

```python
from backend.perception.manager import PerceptionManager

# Start monitoring
manager = PerceptionManager(
    capture_interval=1.0,  # seconds
    window_size=20,        # seconds
    on_data_captured=handle_event
)

await manager.start()

# Get statistics
stats = manager.get_stats()
print(f"Captured {stats['total_events']} events")
```

See [Perception Layer Guide](./perception-layer.md).

## Processing Layer

Transform events into activities:

```python
from backend.processing.pipeline import ProcessingPipeline

pipeline = ProcessingPipeline(config)

# Process buffered events
await pipeline.process_batch()

# Manual processing
events = await pipeline.extract_events(screenshots)
activity = await pipeline.create_activity(events)
```

See [Processing Layer Guide](./processing-layer.md).

## Agent System

Create task recommendation agents:

```python
from backend.agents.base import BaseAgent

class MyAgent(BaseAgent):
    async def can_handle(self, activity: Activity) -> bool:
        """Determine if this agent should process the activity"""
        return 'coding' in activity.keywords
    
    async def execute(self, activity: Activity) -> Task:
        """Generate task recommendation"""
        analysis = await self._analyze_with_llm(activity)
        
        return Task(
            title=analysis['title'],
            description=analysis['description'],
            priority='high',
            source_activity_id=activity.id
        )

# Register agent
from backend.agents import AgentFactory
AgentFactory.register(MyAgent())
```

See [Agents Guide](./agents.md).

## Best Practices

### Type Hints

```python
# ✅ Use precise type hints
def process_activity(activity: Activity) -> list[Task]:
    ...

# ❌ Avoid Any
def process_activity(activity: Any) -> Any:
    ...
```

### Async/Await

```python
# ✅ Use async for I/O operations
async def fetch_data() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# ❌ Don't block the event loop
def fetch_data() -> dict:
    return requests.get(url).json()  # Blocks
```

### Database Transactions

```python
# ✅ Use context manager for transactions
with db._get_conn() as conn:
    conn.execute(queries.INSERT_ACTIVITY, (...))
    conn.execute(queries.INSERT_SCREENSHOTS, (...))
    conn.commit()  # Atomic

# ❌ Don't leave connections open
conn = db._get_conn()
conn.execute(...)  # May leak connection
```

### Logging

```python
from backend.core.logger import logger

# ✅ Use appropriate log levels
logger.debug(f"Processing activity: {activity.id}")
logger.info(f"Activity created: {activity.id}")
logger.warning(f"Slow LLM response: {duration}s")
logger.error(f"Failed to save activity: {error}")

# ❌ Don't use print()
print("Debug message")  # Bad
```

## Testing

```python
import pytest
from backend.handlers.activity import get_activities

@pytest.mark.asyncio
async def test_get_activities():
    request = GetActivitiesRequest(
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    
    response = await get_activities(request)
    
    assert response['success']
    assert len(response['activities']) > 0
```

## Debugging

### Check Logs

```bash
tail -f ~/.config/ido/logs/app.log
```

### Use FastAPI Docs

```bash
uvicorn app:app --reload
# Visit http://localhost:8000/docs
# Test endpoints interactively
```

### Type Checking

```bash
uv run ty check
```

## Next Steps

- 📡 [API Handlers](./api-handlers.md) - Master the handler system
- 👁️ [Perception Layer](./perception-layer.md) - Capture user activity
- ⚙️ [Processing Layer](./processing-layer.md) - Transform data
- 🤖 [Agents](./agents.md) - Build intelligent agents
- 🗄️ [Database Reference](../../reference/database-schema.md) - Schema details
