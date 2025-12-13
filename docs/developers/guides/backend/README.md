# Backend Development Guide

This guide covers backend development for iDO, including API handlers, perception layer, processing pipeline, and agents.

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
│   ├── summarizer.py  # LLM interaction layer
│   └── image_manager.py
│
├── agents/            # AI agents
│   ├── raw_agent.py       # Scene extraction (screenshots → text)
│   ├── action_agent.py    # Action extraction
│   ├── knowledge_agent.py # Knowledge extraction
│   ├── event_agent.py     # Event aggregation
│   └── supervisor.py      # Quality validation
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
  userInput: 'test', // camelCase in TypeScript
  maxResults: 10
})

console.log(result.totalCount) // Auto-converted from snake_case
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

## Processing Layer

Transform screenshots into structured data using a two-step approach:

```python
from backend.processing.pipeline import ProcessingPipeline

pipeline = ProcessingPipeline(config)

# New architecture: RawAgent → ActionAgent → KnowledgeAgent
# Step 1: RawAgent extracts scene descriptions from screenshots (images → text)
# Step 2: ActionAgent extracts actions from scenes (text → actions)
# Step 3: KnowledgeAgent extracts knowledge from scenes or actions (text → knowledge)
await pipeline.process_batch()

# Benefits:
# - Process images once, reuse text data multiple times
# - 75% token reduction for action extraction (16k → 4k tokens)
# - Better consistency (all agents work from same scene data)
# - Scenes are memory-only, auto garbage-collected
```

### Scene-Based Extraction Pattern

```python
from backend.agents.raw_agent import RawAgent
from backend.agents.action_agent import ActionAgent
from backend.agents.knowledge_agent import KnowledgeAgent

# Initialize agents
raw_agent = RawAgent()
action_agent = ActionAgent()
knowledge_agent = KnowledgeAgent()

# Step 1: Extract scene descriptions (memory-only)
scenes = await raw_agent.extract_scenes(
    records,  # Raw screenshots
    keyboard_records=keyboard_records,
    mouse_records=mouse_records
)

# Scene structure (in-memory dictionary):
# {
#     "screenshot_index": 0,
#     "screenshot_hash": "abc123...",
#     "timestamp": "2025-01-01T12:00:00",
#     "visual_summary": "Code editor showing auth.ts file...",
#     "detected_text": "function loginUser() { ... }",
#     "ui_elements": "Code editor, file explorer, terminal",
#     "application_context": "VS Code, working on auth",
#     "inferred_activity": "Writing authentication code",
#     "focus_areas": "Code editing area, function implementation"
# }

# Step 2: Extract actions from scenes (text-only, NO images)
actions_count = await action_agent.extract_and_save_actions_from_scenes(
    scenes,
    keyboard_records=keyboard_records,
    mouse_records=mouse_records
)

# Step 3: Extract knowledge from scenes (text-only, NO images)
knowledge_count = await knowledge_agent.extract_knowledge_from_scenes(
    scenes,
    keyboard_records=keyboard_records,
    mouse_records=mouse_records
)

# Scenes are automatically garbage-collected after processing
```

## Agent System

The agent system consists of specialized agents for different extraction tasks:

### RawAgent - Scene Extraction

Converts screenshots into structured text descriptions:

```python
from backend.agents.raw_agent import RawAgent

raw_agent = RawAgent()

# Extract high-level semantic information from screenshots
scenes = await raw_agent.extract_scenes(
    records,  # List of RawRecord (screenshots)
    keyboard_records=keyboard_records,
    mouse_records=mouse_records
)

# Returns memory-only scene descriptions (no database storage)
# Each scene contains:
# - visual_summary: What's happening on screen
# - detected_text: Visible important text
# - ui_elements: Main interface components
# - application_context: What app/tool is being used
# - inferred_activity: What the user seems to be doing
# - focus_areas: Key areas of attention

# Statistics
stats = raw_agent.get_stats()
print(f"Extracted {stats['scenes_extracted']} scenes")
```

### ActionAgent - Action Extraction

Extracts user work phases from scene descriptions:

```python
from backend.agents.action_agent import ActionAgent

action_agent = ActionAgent()

# Extract actions from scenes (text-only, no images)
saved_count = await action_agent.extract_and_save_actions_from_scenes(
    scenes,  # Scene descriptions from RawAgent
    keyboard_records=keyboard_records,
    mouse_records=mouse_records,
    enable_supervisor=False  # Optional quality validation
)

# Returns: Number of actions saved to database
# Actions contain:
# - title: Specific work phase description
# - description: Complete work context
# - keywords: High-distinctiveness tags
# - scene_index: References to relevant scenes [0, 1, 2...]
# - extract_knowledge: Flag for knowledge extraction
```

### KnowledgeAgent - Knowledge Extraction

Extracts reusable knowledge from scene descriptions or actions:

```python
from backend.agents.knowledge_agent import KnowledgeAgent

knowledge_agent = KnowledgeAgent()

# Option 1: Extract knowledge directly from scenes
knowledge_count = await knowledge_agent.extract_knowledge_from_scenes(
    scenes,  # Scene descriptions from RawAgent
    keyboard_records=keyboard_records,
    mouse_records=mouse_records,
    enable_supervisor=True  # Quality validation enabled
)

# Option 2: Extract knowledge from a specific action
await knowledge_agent.extract_knowledge_from_action(
    action_id="action_123",
    enable_supervisor=True
)

# Periodic tasks
await knowledge_agent.start()  # Starts merge and catchup tasks
# - Merge task: Every 20 minutes, merges related knowledge
# - Catchup task: Every 5 minutes, processes pending extractions
```

### Complete Extraction Pipeline Example

```python
# Full pipeline: Screenshots → Scenes → Actions → Knowledge

# Step 1: Extract scenes
scenes = await raw_agent.extract_scenes(records, keyboard_records, mouse_records)

# Step 2: Extract actions from scenes
actions_count = await action_agent.extract_and_save_actions_from_scenes(
    scenes, keyboard_records, mouse_records
)

# Step 3: Knowledge extraction happens automatically
# - If action has extract_knowledge=true, KnowledgeAgent triggered
# - Or extract directly from scenes:
knowledge_count = await knowledge_agent.extract_knowledge_from_scenes(
    scenes, keyboard_records, mouse_records
)

# Memory cleanup: Scenes auto garbage-collected after processing
```

### Token Usage Optimization

The new architecture significantly reduces token usage:

```python
# OLD ARCHITECTURE (deprecated):
# - ActionAgent: 20 screenshots × 800 tokens = 16,000 tokens
# - KnowledgeAgent: 6 screenshots × 800 tokens = 4,800 tokens
# - Total: ~20,800 tokens per cycle

# NEW ARCHITECTURE:
# - RawAgent: 20 screenshots × 800 tokens = 16,000 tokens (ONE TIME)
# - RawAgent output: ~4,000 tokens (scene descriptions, text-only)
# - ActionAgent: ~4,000 tokens (text-only, NO IMAGES)
# - KnowledgeAgent: ~4,000 tokens (text-only, NO IMAGES)
# - Total first cycle: ~24,000 tokens
#
# BENEFIT: If extracting both actions and knowledge from same scenes:
# - Second agent only uses ~4k tokens instead of ~5k
# - 75% reduction for action extraction (16k → 4k)
# - Better consistency: both agents work from identical scene data
```

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

- 🔄 [Data Flow](../../architecture/data-flow.md) - Understand how data moves through the system
- 🏗️ [Architecture](../../architecture/README.md) - System design overview
- 💻 [Frontend Guide](../frontend/README.md) - Build UI components
- 🚀 [Development Workflow](../../getting-started/development-workflow.md) - Common development tasks
