# Data Flow

This document describes how data flows through iDO's three-layer architecture, from raw system events to AI-powered task recommendations.

## Complete Data Flow

```
[T=0s] User Action
         ↓
      System Event (keyboard/mouse/screen)
         ↓
      Perception Layer Captures
         ↓
      RawRecord Created
         ↓
      Stored in 20s Sliding Window

[T=10s] Processing Triggered (periodic)
         ↓
      1. Read RawRecords from buffer
      2. Filter noise and duplicates
      3. Aggregate into events
      4. Call LLM for summarization
      5. Merge with existing activities
      6. Calculate version number
      7. Persist to SQLite
      8. Emit Tauri events

[Async] Frontend Sync
         ↓
      Listen to 'activity-created' event
         ↓
      Fetch incremental updates (if needed)
         ↓
      Update Zustand store
         ↓
      React components re-render
         ↓
      User sees updated timeline

[On-Demand] Agent Analysis
         ↓
      User clicks "Generate Tasks"
         ↓
      Load activity from database
         ↓
      Route to appropriate agents
         ↓
      Agents analyze and recommend tasks
         ↓
      Save tasks to database
         ↓
      Display recommendations
```

## Detailed Flow by Layer

### Perception Layer Flow

```python
# 1. User types 'hello'
Keyboard Event: key='h', action='press'
    ↓
KeyboardCapture._on_press()
    ↓
RawRecord(type="keyboard", timestamp=now(), data={"key": "h"})
    ↓
SlidingWindowStorage.add(record)
    ↓
EventBuffer.add(record)

# 2. Screenshot taken (every 1s)
ScreenshotCapture.capture()
    ↓
mss.grab(monitor_index=1)
    ↓
Calculate perceptual hash
    ↓
if hash != last_hash:  # Not duplicate
    RawRecord(type="screenshot", data={"path": "...", "hash": "..."})
    ↓
    SlidingWindowStorage.add(record)

# 3. Cleanup old records (> 20s)
Every 60s: SlidingWindowStorage._cleanup_expired_records()
```

### Processing Layer Flow

```python
# Triggered every 10 seconds by ProcessingPipeline

1. Read Buffer
   buffer_events = perception_manager.get_buffered_events()
   # Returns ~200 events from last 10 seconds

2. Filter Events
   filtered = filter_important_events(buffer_events)
   # Remove: duplicate screenshots, spam clicks, etc.

3. Extract Events with LLM
   prompt = build_event_extraction_prompt(filtered)
   response = llm_client.call(prompt)
   events = parse_llm_response(response)
   # events = [
   #   {title: "...", description: "...", keywords: [...], image_index: [...]},
   #   ...
   # ]

4. Create/Update Activities
   for event in events:
       existing = find_matching_activity(event)
       if existing and should_merge(existing, event):
           activity = merge_activity(existing, event)
           activity.version += 1
       else:
           activity = create_new_activity(event)
           activity.version = 1
       
       db.save_activity(activity)
       emit_event('activity-updated' if existing else 'activity-created', activity)

5. Clear Buffer
   perception_manager.event_buffer.clear()
```

### Consumption Layer Flow

```typescript
// Frontend React Application

// 1. Initial Load
useEffect(() => {
  activityStore.fetchTimelineData(dateRange)
}, [dateRange])

// 2. Real-time Updates
useTauriEvents({
  'activity-created': (payload) => {
    // New activity created
    activityStore.addActivity(payload)
  },
  
  'activity-updated': (payload) => {
    // Existing activity modified
    activityStore.updateActivity(payload)
  }
})

// 3. Incremental Sync (fallback)
setInterval(() => {
  const lastVersion = activityStore.maxVersion
  const updates = await apiClient.getIncrementalActivities({
    sinceVersion: lastVersion
  })
  activityStore.mergeActivities(updates)
}, 30000)  // Every 30s

// 4. Agent Analysis
const handleGenerateTasks = async (activityId: string) => {
  const tasks = await apiClient.analyzeActivity({ activityId })
  agentStore.addTasks(tasks)
}
```

## Data Transformation Examples

### Example 1: Code Editing Session

```
[Input] RawRecords (20 seconds of activity)
├── keyboard: 145 key presses
├── mouse: 12 clicks
└── screenshots: 20 images

[Processing] Event Extraction
LLM analyzes screenshots + event counts
    ↓
[Output] Events
{
  "events": [
    {
      "title": "[VSCode] — Editing Python file (backend/core/coordinator.py)",
      "description": "User is implementing a new feature in the coordinator module. Modified the _init_managers method to add error handling. Added logging statements. The code editor shows Python syntax highlighting with autocomplete suggestions.",
      "keywords": ["python", "vscode", "backend", "coordinator", "coding"],
      "image_index": [0, 5, 12, 19]  // Key screenshots
    }
  ],
  "knowledge": [],
  "todos": [
    {
      "title": "Add unit tests for coordinator error handling",
      "description": "The new error handling code needs test coverage",
      "keywords": ["testing", "coordinator", "python"]
    }
  ]
}

[Aggregation] Activity Merging
Check if related to existing "VSCode coding session" activity
    ↓
If yes: Merge and extend time range
If no: Create new activity

[Output] Activity
{
  "id": "act_abc123",
  "version": 3,  // Incremented from previous version
  "title": "VSCode coding session: coordinator.py",
  "description": "Extended coding session working on backend coordinator...",
  "start_time": "2024-01-15 10:00:00",
  "end_time": "2024-01-15 10:20:00",  // Extended
  "keywords": ["python", "vscode", "backend", "coordinator", "coding"],
  "screenshots": ["abc1.jpg", "abc2.jpg", ...],
  "related_todos": ["todo_xyz"]
}

[Frontend] Timeline Update
activityStore receives 'activity-updated' event
    ↓
Update existing activity card in timeline
    ↓
Show badge: "Updated 5 seconds ago"
```

### Example 2: Research Session

```
[Input] RawRecords
├── keyboard: 45 key presses (mostly search queries)
├── mouse: 35 clicks (link navigation)
└── screenshots: 20 browser screenshots

[Processing] Event Extraction
    ↓
[Output] Events
{
  "events": [
    {
      "title": "[Chrome] — Researching Rust async programming",
      "description": "User is reading documentation about Tokio runtime...",
      "keywords": ["rust", "async", "tokio", "research"],
      "image_index": [2, 8, 15]
    }
  ],
  "knowledge": [
    {
      "title": "Tokio is a Rust async runtime",
      "description": "Tokio provides async/await support for Rust with features like multi-threaded runtime, timer, sync primitives...",
      "keywords": ["rust", "tokio", "async", "runtime"]
    }
  ]
}

[Agent Analysis] CodingAgent triggered
    ↓
[Output] Tasks
[
  {
    "title": "Try implementing async handler with Tokio",
    "description": "Based on research, experiment with Tokio runtime in the backend",
    "priority": "medium",
    "status": "pending"
  }
]
```

## State Management Flow

### Zustand Store Updates

```typescript
// Activity Store
interface ActivityState {
  timelineData: Activity[]
  maxVersion: number
  loading: boolean
  
  // Optimistic updates
  addActivity: (activity: Activity) => void
  updateActivity: (activity: Activity) => void
  
  // Batch sync
  fetchTimelineData: (range: DateRange) => Promise<void>
  fetchIncremental: (sinceVersion: number) => Promise<void>
}

// Update flow
1. Event received → addActivity() called
2. Store updates timelineData array
3. maxVersion updated
4. React components subscribed to timelineData re-render
5. User sees new card with animation
```

### Event-Driven Architecture

```typescript
// Backend emits
await emit_event('activity-created', {
  id: 'act_123',
  version: 1,
  title: '...',
  // ... full activity data
})

// Frontend receives
useTauriEvents({
  'activity-created': (payload) => {
    // Optimistic update
    activityStore.addActivity(payload)
    
    // Show notification
    toast.success('New activity captured')
  }
})
```

## Database Flow

### Write Path

```python
# Processing layer writes
db = get_db_manager()

with db._get_conn() as conn:
    # Insert or update activity
    conn.execute(queries.UPSERT_ACTIVITY, (
        activity.id,
        activity.version,
        activity.title,
        json.dumps(activity.keywords),
        activity.start_time,
        activity.end_time,
        activity.description
    ))
    
    # Insert screenshots
    for screenshot in activity.screenshots:
        conn.execute(queries.INSERT_SCREENSHOT, (
            screenshot.path,
            screenshot.activity_id,
            screenshot.timestamp
        ))
    
    conn.commit()
```

### Read Path

```python
# API handler reads
@api_handler(body=GetActivitiesRequest)
async def get_activities(body: GetActivitiesRequest) -> dict:
    db = get_db_manager()
    
    activities = db.execute(
        queries.SELECT_ACTIVITIES_BY_DATE_RANGE,
        (body.start_date, body.end_date)
    )
    
    # Lazy load screenshots
    for activity in activities:
        if body.include_screenshots:
            activity.screenshots = db.execute(
                queries.SELECT_SCREENSHOTS_BY_ACTIVITY,
                (activity.id,)
            )
    
    return {"activities": activities}
```

## Performance Optimizations

### 1. Incremental Updates

```typescript
// Only fetch changed activities
const lastVersion = localStorage.getItem('lastSyncVersion')
const updates = await apiClient.getIncrementalActivities({
  sinceVersion: parseInt(lastVersion)
})

// Merge into existing state
activityStore.mergeActivities(updates)

// Update last known version
localStorage.setItem('lastSyncVersion', updates.maxVersion)
```

### 2. Virtual Scrolling

```typescript
// Only render visible items
<StickyTimelineGroup
  items={timelineData}  // Could be 1000+ activities
  renderItem={(activity) => <ActivityCard />}
  // Only ~20 cards rendered at a time
/>
```

### 3. LLM Caching

```python
# Cache LLM responses to avoid duplicate calls
@lru_cache(maxsize=100)
def extract_events(screenshot_hashes: tuple) -> List[Event]:
    # If same screenshots seen before, return cached result
    return llm_client.call(prompt)
```

### 4. Database Indexing

```sql
-- Fast queries with proper indexes
CREATE INDEX idx_activities_date ON activities(start_time, end_time);
CREATE INDEX idx_activities_version ON activities(version);
CREATE INDEX idx_screenshots_activity ON screenshots(activity_id);
```

## Error Handling Flow

```python
# Backend error handling
try:
    events = await extract_events(buffer)
except LLMError as e:
    logger.error(f"LLM extraction failed: {e}")
    # Fallback: save raw events without LLM
    events = create_basic_events(buffer)
except DatabaseError as e:
    logger.error(f"DB save failed: {e}")
    # Retry with exponential backoff
    await retry_with_backoff(save_events, events)
finally:
    # Always clear buffer to prevent memory leak
    buffer.clear()
```

```typescript
// Frontend error handling
try {
  await activityStore.fetchTimelineData(range)
} catch (error) {
  // Show user-friendly message
  toast.error('Failed to load activities. Retrying...')
  
  // Automatic retry
  setTimeout(() => activityStore.fetchTimelineData(range), 3000)
}
```

## Next Steps

- 🏗️ [Three-Layer Design](./three-layer-design.md) - Understand each layer's role
- 🛠️ [Tech Stack](./tech-stack.md) - Learn about technology choices
- 🐍 [Backend Development](../guides/backend/README.md) - Implement data processing
- 💻 [Frontend Development](../guides/frontend/README.md) - Build UI components
