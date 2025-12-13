# Three-Layer Design

iDO's core architecture consists of three distinct layers, each with specific responsibilities. This separation enables clean data flow, easy testing, and maintainable code.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                 Consumption Layer (消费层)                    │
│              AI Analysis → Recommendations → UI              │
│                                                              │
│  Responsibilities:                                           │
│  • Activity visualization and analytics                      │
│  • Task recommendations via agents                           │
│  • User interaction and feedback                             │
│  • Real-time UI updates                                      │
│                                                              │
│  Components:                                                 │
│  • React views and components                                │
│  • Zustand stores                                            │
│  • Agent execution results                                   │
└───────────────────────▲──────────────────────────────────────┘
                        │ Activities + Tasks
                        │
┌──────────────────────────────────────────────────────────────┐
│                 Processing Layer (处理层)                     │
│    RawAgent → ActionAgent → KnowledgeAgent → EventAgent     │
│                                                              │
│  Responsibilities:                                           │
│  • Scene extraction from screenshots (images → text)         │
│  • Action extraction from scenes (text-only)                 │
│  • Knowledge extraction from scenes/actions (text-only)      │
│  • Activity aggregation (every 10 minutes)                   │
│  • Database persistence                                      │
│  • 75% token reduction for downstream agents                 │
│                                                              │
│  Components:                                                 │
│  • RawAgent (scene extraction)                               │
│  • ActionAgent (action extraction)                           │
│  • KnowledgeAgent (knowledge extraction)                     │
│  • EventAgent (activity aggregation)                         │
│  • ProcessingPipeline (orchestration)                        │
│  • LLMClient (OpenAI-compatible APIs)                        │
│  • Database repositories                                     │
└───────────────────────▲──────────────────────────────────────┘
                        │ RawRecords + Events
                        │
┌──────────────────────────────────────────────────────────────┐
│                 Perception Layer (感知层)                     │
│            Keyboard → Mouse → Screenshots → Buffer           │
│                                                              │
│  Responsibilities:                                           │
│  • Real-time event capture (200ms cycle)                     │
│  • Screenshot acquisition and deduplication                  │
│  • 20-second sliding window buffering                        │
│  • Platform-specific implementations                         │
│                                                              │
│  Components:                                                 │
│  • KeyboardCapture                                           │
│  • MouseCapture                                              │
│  • ScreenshotCapture                                         │
│  • SlidingWindowStorage                                      │
└──────────────────────────────────────────────────────────────┘
```

## Layer 1: Perception (Capture)

### Purpose

Collect raw user activity data from system-level sources.

### Data Sources

#### 1. Keyboard Events

```python
# Platform-specific implementations
# backend/perception/platforms/macos/keyboard.py
# backend/perception/platforms/windows/keyboard.py
# backend/perception/platforms/linux/keyboard.py

RawRecord(
    type="keyboard",
    timestamp=datetime.now(),
    data={
        "key": "a",
        "action": "press",
        "modifiers": ["ctrl"]
    }
)
```

**Captured**:

- Key presses and releases
- Modifier keys (Ctrl, Shift, Alt, Cmd)
- Key combinations (Ctrl+C, etc.)

**Not Captured**:

- Actual typed text (privacy)
- Passwords or sensitive fields

#### 2. Mouse Events

```python
RawRecord(
    type="mouse",
    timestamp=datetime.now(),
    data={
        "action": "click",
        "button": "left",
        "position": {"x": 500, "y": 300}
    }
)
```

**Captured**:

- Clicks (left, right, middle)
- Scrolling
- Important movements (heuristic-based)

**Not Captured**:

- Every mouse movement (too noisy)
- Drag positions (unless important)

#### 3. Screenshots

```python
RawRecord(
    type="screenshot",
    timestamp=datetime.now(),
    data={
        "monitor_index": 1,
        "path": "/screenshots/abc123.jpg",
        "hash": "phash:d4b5...",
        "width": 1920,
        "height": 1080
    }
)
```

**Features**:

- Per-monitor capture
- Perceptual hash deduplication
- Configurable quality and resolution
- Automatic expiration

### Sliding Window Buffer

```
Timeline: [────────|──────20s window──────|→ Now]
                   ↑                       ↑
              Expires after 20s      Latest events
```

**Benefits**:

- Bounded memory usage
- Prevents data accumulation
- Fast cleanup (O(1) expiration)

### Platform Abstractions

```python
# Factory pattern for cross-platform support
def create_keyboard_monitor(callback):
    if platform.system() == "Darwin":
        return MacOSKeyboardCapture(callback)
    elif platform.system() == "Windows":
        return WindowsKeyboardCapture(callback)
    else:
        return LinuxKeyboardCapture(callback)
```

**Implementations**:

- macOS: Uses `pynput` with CoreGraphics
- Windows: Uses `pynput` with Windows API
- Linux: Uses `pynput` with X11/Wayland

## Layer 2: Processing (Analyze)

### Purpose

Transform raw screenshots into meaningful, LLM-summarized activities using a two-step extraction approach.

### Processing Pipeline

```python
# Triggered every 30 seconds (configurable)
# Two-step extraction: RawAgent → ActionAgent → KnowledgeAgent

1. Read RawRecords from buffer
   ↓
2. Filter noise (duplicate screenshots, spam clicks)
   ↓
3. Accumulate 20+ screenshots (threshold)
   ↓
4. RawAgent: Extract scene descriptions (images → text)
   │  Input:  20 screenshots (~16k tokens with images)
   │  Output: Scene descriptions (~4k tokens, pure text)
   │  - visual_summary: What's happening on screen
   │  - detected_text: Visible important text
   │  - ui_elements: Main interface components
   │  - application_context: What app/tool is being used
   │  - inferred_activity: What the user seems to be doing
   │  - focus_areas: Key areas of attention
   ↓
5. ActionAgent: Extract actions from scenes (text-only, NO images)
   │  Input:  Scene descriptions (~4k tokens)
   │  Output: Actions with scene_index references
   │  - 75% token reduction vs old approach
   ↓
6. KnowledgeAgent: Extract knowledge from scenes/actions (text-only)
   │  Input:  Scene descriptions or actions (~4k tokens)
   │  Output: Knowledge items
   ↓
7. Persist actions/knowledge to database
   ↓
8. Emit 'action-created', 'knowledge-created' events
   ↓
9. Every 10min: EventAgent aggregates actions → activities
   ↓
10. Scenes auto garbage-collected (memory-only)
```

**Benefits of Two-Step Extraction**:

- Process images once, reuse text data multiple times
- 75% token reduction for downstream agents
- Better consistency (all agents work from same scene data)
- Memory-only scene descriptions (no database overhead)

### Scene Extraction (RawAgent)

**Purpose**: Convert screenshots into structured text descriptions for downstream processing.

**Input**: Raw screenshots + keyboard/mouse summaries

**LLM Prompt** (from `prompts_en.toml` - `raw_extraction`):

```
Extract high-level semantic information from EACH screenshot.

For each screenshot, provide:
- visual_summary: What's happening on screen (1-2 sentences)
- detected_text: Important visible text (code, errors, headlines)
- ui_elements: Main interface components
- application_context: What app/tool is being used (ONLY if clearly identifiable)
- inferred_activity: What the user seems to be doing
- focus_areas: Key areas of attention

Format: JSON with scenes array
```

**Output** (memory-only, NOT stored in database):

```python
scenes = [
    {
        "screenshot_index": 0,
        "screenshot_hash": "abc123...",
        "timestamp": "2025-01-01T12:00:00",
        "visual_summary": "Code editor showing auth.ts file...",
        "detected_text": "function loginUser() { ... }",
        "ui_elements": "Code editor, file explorer, terminal",
        "application_context": "VS Code, working on auth",
        "inferred_activity": "Writing authentication code",
        "focus_areas": "Code editing area, function implementation"
    },
    # ... more scenes
]
```

### Action Extraction (ActionAgent)

**Purpose**: Extract user work phases from scene descriptions (text-only).

**Input**: Scene descriptions (text) + keyboard/mouse summaries

**LLM Prompt** (from `prompts_en.toml` - `action_from_scenes`):

```
Based on these scene descriptions, extract the user's main work phases (actions).

For each action, provide:
- title: [App/Tool/Category] — [Action] [Object] ([Context])
- description: Complete work phase (where, what, did what, why, result)
- keywords: ≤5 high-distinctiveness tags
- scene_index: [0, 1, 2...] - References to relevant scenes (zero-based)
- extract_knowledge: true/false - Whether this action contains extractable knowledge

Format: JSON with actions array
```

**Output**:

```json
{
  "actions": [
    {
      "title": "Cursor — Implement user login feature in auth.ts",
      "description": "User is implementing authentication middleware...",
      "keywords": ["auth", "typescript", "login", "middleware"],
      "scene_index": [0, 5, 12, 19],
      "extract_knowledge": true
    }
  ]
}
```

### Knowledge Extraction (KnowledgeAgent)

**Purpose**: Extract reusable knowledge from scene descriptions or actions (text-only).

**Input**: Scene descriptions (text) + keyboard/mouse summaries

**LLM Prompt** (from `prompts_en.toml` - `knowledge_from_scenes`):

```
Based on scene descriptions, extract reusable knowledge points.

For each knowledge item:
- title: Core topic (e.g., "Docker COPY instruction relative path rules")
- description: Self-contained explanation (concept, scenario, solution, insights)
- keywords: ≤5 professional terms or concept tags

Format: JSON with knowledge array
```

**Output**:

```json
{
  "knowledge": [
    {
      "title": "Docker COPY instruction relative path rules",
      "description": "When using COPY in Dockerfile, paths must be relative...",
      "keywords": ["docker", "dockerfile", "copy", "paths"]
    }
  ]
}
```

### Activity Aggregation

**Merging Criteria**:

```python
def should_merge(activity1: Activity, activity2: Activity) -> bool:
    # Merge if:
    # - Same application
    # - Same goal/object
    # - Time gap < 10 minutes
    # - Continuous progression
    return (
        activity1.app == activity2.app and
        similarity(activity1.description, activity2.description) > 0.7 and
        activity2.start_time - activity1.end_time < timedelta(minutes=10)
    )
```

**Benefits**:

- Reduces fragmentation
- Creates coherent activity sessions
- Better for LLM context

### Incremental Updates

```python
# Version tracking for efficient sync
Activity(
    id="abc123",
    version=5,  # Incremented on each update
    start_time="2024-01-01 10:00:00",
    end_time="2024-01-01 10:15:00",
    description="...",
    updated_at="2024-01-01 10:15:30"
)
```

**Frontend sync**:

```typescript
// Only fetch activities updated since last version
const activities = await apiClient.getIncrementalActivities({
  sinceVersion: lastKnownVersion
})
```

## Layer 3: Consumption (Recommend)

### Purpose

Provide value to users through visualization and task recommendations.

### Frontend Components

#### 1. Activity Timeline

```typescript
// src/views/Activity/index.tsx
const ActivityView = () => {
  const { timelineData } = useActivityStore()

  return (
    <StickyTimelineGroup
      items={timelineData}
      getDate={(activity) => activity.startTimestamp}
      renderItem={(activity) => <ActivityCard activity={activity} />}
    />
  )
}
```

**Features**:

- Date-grouped with sticky headers
- Infinite scroll with virtualization
- Real-time updates via events
- Search and filtering

#### 2. Agent System

```python
# backend/agents/coding_agent.py
class CodingAgent(BaseAgent):
    async def can_handle(self, activity: Activity) -> bool:
        return any(keyword in activity.keywords
                  for keyword in ['code', 'programming', 'debug'])

    async def execute(self, activity: Activity) -> Task:
        # Analyze code-related activity
        # Generate task recommendations
        return Task(
            title="Review code changes",
            description="...",
            priority="high"
        )
```

**Agent Flow**:

```
User clicks "Generate Tasks"
    ↓
Frontend calls apiClient.analyzeActivity(activityId)
    ↓
Backend loads activity from DB
    ↓
AgentFactory routes to appropriate agents
    ↓
Each agent analyzes and generates tasks
    ↓
Tasks saved to DB and returned
    ↓
Frontend displays task recommendations
```

### Real-Time Updates

```typescript
// Event-driven architecture
useTauriEvents({
  'activity-created': (payload) => {
    activityStore.addActivity(payload)
  },
  'activity-updated': (payload) => {
    activityStore.updateActivity(payload)
  },
  'task-recommended': (payload) => {
    agentStore.addTask(payload)
  }
})
```

**Benefits**:

- No polling needed
- Instant UI updates
- Reduced backend load
- Better UX

## Data Model Hierarchy

```
RawRecord (Lowest Level)
    ↓ Processed by
Event (Mid Level)
    ↓ Aggregated into
Activity (High Level)
    ↓ Analyzed by agents
Task (Business Level)
```

### Type Definitions

```python
# backend/models/raw_record.py
class RawRecord(BaseModel):
    type: Literal["keyboard", "mouse", "screenshot"]
    timestamp: datetime
    data: Dict[str, Any]

# backend/models/event.py
class Event(BaseModel):
    title: str
    description: str
    keywords: List[str]
    image_indices: List[int]
    timestamp: datetime

# backend/models/activity.py
class Activity(BaseModel):
    id: str
    version: int
    start_time: datetime
    end_time: datetime
    description: str
    keywords: List[str]
    screenshots: List[str]

# backend/models/task.py
class Task(BaseModel):
    id: str
    title: str
    description: str
    priority: Literal["low", "medium", "high"]
    status: Literal["pending", "in_progress", "completed"]
    source_activity_id: str
```

## Layer Isolation Benefits

### 1. Independent Testing

```python
# Test perception layer without processing
def test_keyboard_capture():
    events = []
    capture = KeyboardCapture(callback=events.append)
    capture.start()
    # Simulate key presses
    assert len(events) > 0

# Test processing without perception
def test_event_extraction():
    raw_records = load_fixture("sample_records.json")
    events = extract_events(raw_records)
    assert len(events) > 0
```

### 2. Easy Replacement

```python
# Swap LLM providers without touching perception
old_client = OpenAIClient()
new_client = AnthropicClient()  # Same interface

# Switch screenshot library without changing processing
from mss import mss  # Current
from PIL import ImageGrab  # Alternative
```

### 3. Clear Contracts

```python
# Each layer has defined input/output
Perception → List[RawRecord]
Processing → List[Activity]
Consumption → UI + List[Task]
```

## Configuration

Each layer is independently configurable:

```toml
# config.toml

[monitoring]  # Perception layer
capture_interval = 1  # seconds
window_size = 20  # seconds

[processing]  # Processing layer
event_extraction_threshold = 20  # screenshots
activity_summary_interval = 600  # seconds

[agents]  # Consumption layer
enable_auto_analysis = true
analysis_cooldown = 300  # seconds
```

## Performance Characteristics

| Layer           | CPU Usage         | Memory                  | Latency     |
| --------------- | ----------------- | ----------------------- | ----------- |
| **Perception**  | Low (background)  | Bounded (20s window)    | Real-time   |
| **Processing**  | Medium (periodic) | Moderate (LLM calls)    | 2-5 seconds |
| **Consumption** | Low (UI only)     | Low (virtual scrolling) | <100ms      |

## Next Steps

- 📊 [Data Flow](./data-flow.md) - See how data transforms through layers
- 🛠️ [Tech Stack](./tech-stack.md) - Technology choices for each layer
- 🐍 [Backend Guide](../guides/backend/README.md) - Implement perception and processing
- 💻 [Frontend Guide](../guides/frontend/README.md) - Build consumption layer UI
