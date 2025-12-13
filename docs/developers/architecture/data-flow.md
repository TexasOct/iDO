# Data Flow

This document describes how data flows through iDO's three-layer architecture, from raw system events to AI-powered task recommendations.

## Agent Processing Pipeline (Complete Chain)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT: User Activity                        │
│                    (Keyboard, Mouse, Screenshots)                   │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER (Capture)                       │
│                                                                     │
│  KeyboardCapture  →  RawRecord(type=KEYBOARD)                      │
│  MouseCapture     →  RawRecord(type=MOUSE)                         │
│  ScreenshotCapture→  RawRecord(type=SCREENSHOT)                    │
│                                                                     │
│  ├─ Deduplication: Per-monitor perceptual hash                     │
│  ├─ Force-save: Every 5s even if no change                         │
│  └─ Buffer: In-memory sliding window (60s)                         │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
                    [Every 30s: Processing Trigger]
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER (Analyze)                       │
│                  Agent Chain: 4-Step Extraction                     │
└─────────────────────────────────────────────────────────────────────┘
                             ↓
    ╔════════════════════════════════════════════════════════════╗
    ║  STEP 1: RawAgent (Scene Extraction)                       ║
    ║  ─────────────────────────────────────────────────────     ║
    ║  Input:  20+ screenshots (deduplicated)                    ║
    ║          + Keyboard/mouse records                          ║
    ║  LLM:    OpenAI-compatible API                             ║
    ║  Tokens: ~16,000 tokens (images + text)                    ║
    ║  Prompt: prompts_en.toml → [prompts.raw_extraction]        ║
    ║                                                            ║
    ║  Output: Scene descriptions (memory-only, NOT stored)      ║
    ║  ┌────────────────────────────────────────────────────┐   ║
    ║  │ Scene 0:                                           │   ║
    ║  │   screenshot_index: 0                              │   ║
    ║  │   screenshot_hash: "abc123..."                     │   ║
    ║  │   timestamp: "2025-01-01T12:00:00"                 │   ║
    ║  │   visual_summary: "Code editor showing..."         │   ║
    ║  │   detected_text: "function login() {...}"          │   ║
    ║  │   ui_elements: "Editor, file explorer, terminal"   │   ║
    ║  │   application_context: "VS Code, auth feature"     │   ║
    ║  │   inferred_activity: "Writing auth code"           │   ║
    ║  │   focus_areas: "Code editing area"                 │   ║
    ║  └────────────────────────────────────────────────────┘   ║
    ║  (20+ scenes in memory)                                    ║
    ╚════════════════════════════════════════════════════════════╝
                             ↓
                    [Pass scenes to next agent]
                             ↓
    ╔════════════════════════════════════════════════════════════╗
    ║  STEP 2: ActionAgent (Action Extraction)                   ║
    ║  ─────────────────────────────────────────────────────     ║
    ║  Input:  Scene descriptions (text-only, NO images)         ║
    ║          + Keyboard/mouse records                          ║
    ║  LLM:    OpenAI-compatible API                             ║
    ║  Tokens: ~4,000 tokens (75% reduction!)                    ║
    ║  Prompt: prompts_en.toml → [prompts.action_from_scenes]    ║
    ║                                                            ║
    ║  Output: Actions (saved to database)                       ║
    ║  ┌────────────────────────────────────────────────────┐   ║
    ║  │ Action 1:                                          │   ║
    ║  │   id: "act_123"                                    │   ║
    ║  │   title: "Cursor — Implement login in auth.ts"    │   ║
    ║  │   description: "User implemented auth middleware..."│   ║
    ║  │   keywords: ["auth", "typescript", "login"]        │   ║
    ║  │   scene_index: [0, 5, 12, 19]  ← References scenes│   ║
    ║  │   screenshot_hash: ["abc123", "def456", ...]       │   ║
    ║  │   timestamp: "2025-01-01T12:00:00"                 │   ║
    ║  │   extract_knowledge: true  ← Flag for Step 3      │   ║
    ║  └────────────────────────────────────────────────────┘   ║
    ║                                                            ║
    ║  Side Effect: Emit 'action-created' event to frontend     ║
    ╚════════════════════════════════════════════════════════════╝
                             ↓
            [If extract_knowledge=true for any action]
                             ↓
    ╔════════════════════════════════════════════════════════════╗
    ║  STEP 3: KnowledgeAgent (Knowledge Extraction)             ║
    ║  ─────────────────────────────────────────────────────     ║
    ║  Trigger: Async task when extract_knowledge=true           ║
    ║                                                            ║
    ║  Option A: Extract from action                             ║
    ║  ├─ Input:  Action details + screenshot thumbnails         ║
    ║  ├─ LLM:    OpenAI-compatible API                          ║
    ║  ├─ Tokens: ~5,000 tokens (action + 6 screenshots)         ║
    ║  └─ Prompt: [prompts.knowledge_from_action]                ║
    ║                                                            ║
    ║  Option B: Extract from scenes (memory)                    ║
    ║  ├─ Input:  Scene descriptions (text-only)                 ║
    ║  ├─ LLM:    OpenAI-compatible API                          ║
    ║  ├─ Tokens: ~4,000 tokens (text-only, NO images)           ║
    ║  └─ Prompt: [prompts.knowledge_from_scenes]                ║
    ║                                                            ║
    ║  Output: Knowledge items (saved to database)               ║
    ║  ┌────────────────────────────────────────────────────┐    ║
    ║  │ Knowledge 1:                                       │    ║
    ║  │   id: "know_456"                                   │    ║
    ║  │   title: "Docker COPY path rules"                  │    ║
    ║  │   description: "COPY uses relative paths..."       │    ║
    ║  │   keywords: ["docker", "dockerfile", "copy"]       │    ║
    ║  │   source_action_id: "act_123"                      │    ║
    ║  │   created_at: "2025-01-01T12:00:00"                │    ║
    ║  └────────────────────────────────────────────────────┘    ║
    ║                                                            ║
    ║  Validation: KnowledgeSupervisor checks quality            ║
    ║  Side Effect: Emit 'knowledge-created' event               ║
    ╚════════════════════════════════════════════════════════════╝
                             ↓
                    [Scenes auto garbage-collected]
                             ↓
            [Actions and knowledge accumulate in database]
                             ↓
                    [Every 10 minutes: Aggregation]
                             ↓
    ╔════════════════════════════════════════════════════════════╗
    ║  STEP 4: EventAgent (Activity Aggregation)                 ║
    ║  ─────────────────────────────────────────────────────     ║
    ║  Trigger: Scheduled task every 10 minutes                  ║
    ║  Input:   Recent actions from database (last 10min)        ║
    ║  LLM:     OpenAI-compatible API                            ║
    ║  Tokens:  Variable (depends on action count)               ║
    ║  Prompt:  prompts_en.toml → [prompts.activity_aggregation] ║
    ║                                                            ║
    ║  Process:                                                  ║
    ║  1. Load unmerged actions from database                    ║
    ║  2. Group by theme/project/time proximity                  ║
    ║  3. LLM aggregates related actions → activities            ║
    ║  4. Validate with ActivitySupervisor                       ║
    ║  5. Save activities to database                            ║
    ║                                                            ║
    ║  Output: Activities (saved to database)                    ║
    ║  ┌────────────────────────────────────────────────────┐   ║
    ║  │ Activity 1:                                        │   ║
    ║  │   id: "activity_789"                               │   ║
    ║  │   version: 1                                       │   ║
    ║  │   title: "Frontend - Auth Feature Development"    │   ║
    ║  │   description: "Implemented authentication..."     │   ║
    ║  │   start_time: "2025-01-01T12:00:00"                │   ║
    ║  │   end_time: "2025-01-01T12:20:00"                  │   ║
    ║  │   source_action_ids: ["act_123", "act_124", ...]  │   ║
    ║  │   keywords: ["auth", "frontend", "typescript"]     │   ║
    ║  └────────────────────────────────────────────────────┘   ║
    ║                                                            ║
    ║  Side Effect: Frontend incremental sync (every 30s)        ║
    ║               NOT via event emission                       ║
    ╚════════════════════════════════════════════════════════════╝
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    CONSUMPTION LAYER (Display)                      │
│                                                                     │
│  Frontend:                                                          │
│  ├─ useTauriEvents: Listen 'action-created', 'knowledge-created'   │
│  ├─ Incremental sync: Fetch new activities every 30s               │
│  └─ UI: Activity timeline, knowledge base, todo list               │
└─────────────────────────────────────────────────────────────────────┘
                             ↓
                    [User sees activity timeline]
```

## Periodic Background Tasks

In addition to the main processing chain, several agents run periodic maintenance tasks:

```
╔════════════════════════════════════════════════════════════╗
║  KnowledgeAgent Background Tasks                           ║
║  ─────────────────────────────────────────────────────     ║
║  Task 1: Knowledge Merge (every 20 minutes)                ║
║  ├─ Load unmerged knowledge items                          ║
║  ├─ LLM merges semantically related knowledge              ║
║  ├─ Save to combined_knowledge table                       ║
║  └─ Soft delete original knowledge items                   ║
║                                                            ║
║  Task 2: Pending Extraction Catchup (every 5 minutes)      ║
║  ├─ Find actions with extract_knowledge=true               ║
║  │   but knowledge_extracted=false                         ║
║  ├─ Extract knowledge for each pending action              ║
║  └─ Mark actions as knowledge_extracted=true               ║
╚════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════╗
║  TodoAgent Background Tasks                                ║
║  ─────────────────────────────────────────────────────     ║
║  Task: Todo Merge (every 20 minutes)                       ║
║  ├─ Load unmerged todo items                               ║
║  ├─ LLM merges related todos                               ║
║  ├─ Save to combined_todos table                           ║
║  └─ Soft delete original todo items                        ║
╚════════════════════════════════════════════════════════════╝
```

## Token Usage Breakdown

Per 30-second processing cycle with 20 screenshots:

| Agent          | Input Type  | Token Count    | Notes                              |
| -------------- | ----------- | -------------- | ---------------------------------- |
| RawAgent       | Images      | ~16,000        | 20 screenshots × 800 tokens/image  |
| ActionAgent    | Text        | ~4,000         | Scene descriptions (75% reduction) |
| KnowledgeAgent | Text/Images | ~4,000-5,000   | Scenes (text) or action (images)   |
| EventAgent     | Text        | Variable       | Depends on action count            |
| **Total**      |             | ~24,000-25,000 | First cycle with all agents        |

**Comparison with old architecture:**

- Old: ActionAgent (16k) + KnowledgeAgent (5k) = ~21k tokens
- New: RawAgent (16k) + ActionAgent (4k) + KnowledgeAgent (4k) = ~24k tokens
- **Benefit**: Better consistency, reusable scenes, same scene data for all agents

## Complete Data Flow (Actual Implementation)

```
[T=0s] User Action
         ↓
      System Event (keyboard/mouse/screen)
         ↓
      Perception Layer Captures
         ↓
      RawRecord Created
         ↓
      Stored in In-Memory Sliding Window (100+ records, auto-cleanup)

[Every 0.2s] Screenshot Capture (concurrent)
         ↓
      ScreenshotCapture.capture_with_interval()
         ↓
      Per-monitor hash comparison (perceptual hash)
         ↓
      If different OR force-save after 5s: Save RawRecord
         ↓
      Storage in deque

[Every 30s] Main Processing Loop
         ↓
      1. Read all RawRecords from buffer (T-30s to now)
      2. Filter noise and deduplicates
      3. Extract screenshots (~20+ threshold)
      4. Accumulate screenshots in-memory
         ↓
         [Screenshot threshold (20) reached]
         ↓
      5. NEW: RawAgent extracts scene descriptions (LLM + images → text)
      6. ActionAgent extracts actions from scenes (text-only, no images)
      7. KnowledgeAgent triggered by actions with extract_knowledge=true
      8. Persist actions, knowledge to SQLite
      9. Emit 'action-created' / 'knowledge-created' events
         (⚠️ NOTE: Scene descriptions are memory-only, auto garbage-collected)

[Every 10 minutes] Activity Summary (separate scheduled task)
         ↓
      Aggregate related activities

[Every 20 minutes] Knowledge/Todo Merge (separate scheduled tasks)
         ↓
      Combine related knowledge and todos

[Event-Driven] Frontend Sync
         ↓
      Listen to 'event-created', 'knowledge-created', 'todo-created' events
         ↓
      Update relevant Zustand stores
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

**Key Timeline:**

- Screenshots captured: **Every 0.2 seconds** (5 per second per monitor)
- Main processing loop: **Every 30 seconds** (first iteration: 100ms)
- Screenshot accumulation threshold: **20 screenshots** (~4 seconds of data)
- Event extraction triggered: When **20+ screenshots** accumulated
- Activity summary: **Every 10 minutes** (600s)
- Knowledge/Todo merge: **Every 20 minutes** (1200s)

## Quick Reference: Configuration & Timings

| Component                   | Configuration                    | Default        | Notes                              |
| --------------------------- | -------------------------------- | -------------- | ---------------------------------- |
| **Perception Layer**        |                                  |                |                                    |
| Screenshot capture interval | `monitoring.capture_interval`    | 0.2s           | Every 200ms per monitor            |
| Screenshot deduplication    | Per-monitor perceptual hash      | Enabled        | Prevents duplicate frames          |
| Force-save interval         | `_force_save_interval`           | 5s             | Save even if no change             |
| Sliding window size         | `monitoring.window_size`         | 60s            | Auto-cleanup after 60s             |
| Keyboard capture            | Record ALL events                | Enabled        | No filtering at capture            |
| Mouse capture               | Important events only            | Enabled        | Clicks, drags; ignore movement     |
| **Processing Layer**        |                                  |                |                                    |
| Main loop interval          | `monitoring.processing_interval` | 30s            | First iteration: 100ms             |
| Screenshot threshold        | `screenshot_threshold`           | 20             | Triggers LLM extraction            |
| Activity summary interval   | `activity_summary_interval`      | 600s (10m)     | Separate scheduled task            |
| Knowledge merge interval    | `knowledge_merge_interval`       | 1200s (20m)    | Separate scheduled task            |
| Todo merge interval         | `todo_merge_interval`            | 1200s (20m)    | Separate scheduled task            |
| **Event Emission**          |                                  |                |                                    |
| Events emitted              | `event-created`                  | Real-time      | Immediately after extraction       |
| Knowledge emitted           | `knowledge-created`              | Real-time      | Immediately after extraction       |
| Todos emitted               | `todo-created`                   | Real-time      | Immediately after extraction       |
| Activities emitted          | `activity-created`               | ❌ NOT EMITTED | Use incremental sync instead       |
| **Frontend Sync**           |                                  |                |                                    |
| Incremental fetch interval  | Periodic                         | 30s            | Fallback for activity updates      |
| Initial data load           | On-demand                        | -              | Triggered on app start/date change |
| Store updates               | Zustand                          | Real-time      | Immediate UI re-render             |

## Detailed Flow by Layer

### Perception Layer Flow

The perception layer continuously captures system events across multiple independent capture threads:

```python
# ===== KEYBOARD CAPTURE (all events recorded) =====
# 1. User types 'hello'
Keyboard Event: key='h', timestamp=1234567890
    ↓
KeyboardCapture.on_press(key)
    ↓
RawRecord(
    type=RecordType.KEYBOARD_RECORD,
    timestamp=1234567890,
    data={"key": "h", "action": "press"}
)
    ↓
PerceptionManager._on_keyboard_event()
    ↓
Stored in sliding window deque (in-memory)

# ===== MOUSE CAPTURE (important events only) =====
# 2. User clicks button
Mouse Event: x=100, y=200, button='left', action='press'
    ↓
MouseCapture.on_click(x, y, button)
    ↓
RawRecord(
    type=RecordType.MOUSE_RECORD,
    timestamp=now(),
    data={"x": 100, "y": 200, "button": "left", "action": "press"}
)
    ↓
Stored in sliding window deque

# ===== SCREENSHOT CAPTURE (every 0.2s per monitor) =====
# 3. Screenshot loop runs continuously
ScreenshotCapture._screenshot_loop()  # Async task
    ↓
    Every 0.2 seconds:
    PerceptionManager.capture_interval = 0.2  # Configurable
    ↓
    For each enabled monitor:
        mss.grab(monitor_index)
        ↓
        Calculate perceptual hash (PIL + hashlib)
        ↓
        if (hash != last_hash) OR (current_time - last_force_save >= 5s):
            ↓
            RawRecord(
                type=RecordType.SCREENSHOT_RECORD,
                timestamp=now(),
                data={
                    "path": "~/.local/share/ido/tmp/screenshots/...",
                    "hash": "abc123def456",
                    "monitor_index": 1,
                    "width": 1920,
                    "height": 1080
                }
            )
            ↓
            PerceptionManager._on_screenshot_event()
            ↓
            Stored in sliding window deque
            Update last_force_save_time[monitor_id] = now()
        else:
            Skip (duplicate detected)

# ===== SLIDING WINDOW MANAGEMENT =====
# 4. Automatic cleanup (every 60s)
PerceptionManager._cleanup_old_records()
    ↓
    For each record in deque:
        if (now() - record.timestamp) > window_size:  # Default: 60s
            Remove from deque
    ↓
    Free memory

# ===== PAUSE ON SCREEN LOCK/SLEEP =====
# 5. System pause handling
When screen locks or system sleeps:
    ↓
KeyboardCapture.pause()
MouseCapture.pause()
ScreenshotCapture.pause()
    ↓
All capture threads stop recording
    ↓
Resume on screen unlock / wake
```

**Key Points:**

- **Keyboard:** ALL key presses recorded (no filtering at capture time)
- **Mouse:** Only important events (clicks, drags) - movement ignored
- **Screenshots:** Every 0.2s per monitor with per-monitor deduplication
- **Force save:** Screenshots saved every 5s even if no visual change
- **Storage:** Pure in-memory deque (not persisted to DB yet)
- **Window size:** Records kept for 60 seconds, older ones auto-cleaned

### Processing Layer Flow

The processing layer runs on a **30-second main loop** with additional scheduled tasks for aggregation:

```python
# ===== MAIN PROCESSING LOOP (every 30 seconds) =====
# First iteration: 100ms delay
# Subsequent iterations: 30s interval (configurable)

async def _processing_loop():
    first_iteration = True
    while is_running:
        wait_time = 0.1 if first_iteration else 30  # seconds
        await asyncio.sleep(wait_time)
        first_iteration = False

        # T=30s: Get all records from last 30 seconds
        end_time = now()
        start_time = last_processed_timestamp or (end_time - 30s)
        raw_records = perception_manager.get_records_in_timeframe(start_time, end_time)

        if raw_records:
            result = await processing_pipeline.process_raw_records(raw_records)
            last_processed_timestamp = max(record.timestamp for record in raw_records)

# ===== RAW RECORD PROCESSING =====
async def process_raw_records(raw_records):
    """
    Process incoming raw records (keyboard, mouse, screenshots)

    NEW ARCHITECTURE (RawAgent → ActionAgent):
    1. Separate by type (keyboard, mouse, screenshots)
    2. Apply filtering to each type
    3. Accumulate screenshots
    4. When threshold reached:
       a. RawAgent extracts scene descriptions (images → text)
       b. ActionAgent extracts actions from scenes (text-only)
    """

    # 1. SEPARATE RECORDS BY TYPE
    screenshots = [r for r in raw_records if r.type == SCREENSHOT_RECORD]
    keyboard = [r for r in raw_records if r.type == KEYBOARD_RECORD]
    mouse = [r for r in raw_records if r.type == MOUSE_RECORD]

    # 2. FILTER NOISE (per event type)
    filtered = event_filter.filter_all_events(raw_records)
    # Removes: duplicate screenshots, spam clicks, etc.

    # 3. ACCUMULATE SCREENSHOTS IN-MEMORY
    screenshot_accumulator.extend(screenshots)

    # 4. CHECK THRESHOLD
    if len(screenshot_accumulator) >= 20:  # Configured threshold
        # NEW: Two-step extraction process
        await _extract_actions_via_raw_agent(
            screenshot_accumulator,
            keyboard_records=keyboard,
            mouse_records=mouse
        )
        screenshot_accumulator.clear()

# ===== NEW: TWO-STEP EXTRACTION WITH RAW AGENT =====
async def _extract_actions_via_raw_agent(screenshots, keyboard_records, mouse_records):
    """
    NEW ARCHITECTURE: Process images once, reuse text everywhere

    Benefits:
    - Images sent to LLM only ONCE (RawAgent)
    - ActionAgent and KnowledgeAgent work with text (~80-90% token savings)
    - Better consistency (both agents work from same scene data)
    - Scenes can be re-processed without re-sending images
    """

    # STEP 1: Extract scene descriptions from screenshots (RawAgent)
    # Input: 20 screenshots (~16k tokens with images)
    # Output: Scene descriptions (~4k tokens, pure text)
    logger.debug("Step 1: Extracting scene descriptions via RawAgent")
    scenes = await raw_agent.extract_scenes(
        screenshots,
        keyboard_records=keyboard_records,
        mouse_records=mouse_records,
    )

    if not scenes:
        logger.warning("RawAgent returned no scenes, skipping extraction")
        return

    # Scene structure (memory-only):
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

    logger.debug(f"RawAgent extracted {len(scenes)} scene descriptions")

    # STEP 2: Extract actions from scene descriptions (ActionAgent)
    # Input: Scene descriptions (~4k tokens, text-only, NO images)
    # Output: Actions with scene_index references
    logger.debug("Step 2: Extracting actions from scenes via ActionAgent (text-only)")
    saved_count = await action_agent.extract_and_save_actions_from_scenes(
        scenes,
        keyboard_records=keyboard_records,
        mouse_records=mouse_records,
    )

    # Action structure:
    # {
    #     "title": "Cursor — Implementing auth.ts middleware",
    #     "description": "Writing authentication middleware in auth.ts...",
    #     "keywords": ["auth", "typescript", "middleware"],
    #     "scene_index": [0, 5, 12, 19],  # References to scenes
    #     "extract_knowledge": true  # Triggers knowledge extraction
    # }

    logger.debug(f"ActionAgent completed: saved {saved_count} actions")

    # STEP 3: Actions are saved to database
    # - screenshot_hash mapped from scene_index
    # - timestamp calculated from scenes
    # - If extract_knowledge=true, async knowledge extraction triggered

    # STEP 4: Scenes auto garbage-collected (memory-only)
    # No cleanup needed - Python GC handles it automatically
    logger.debug("Scene descriptions will be auto garbage-collected")

# ===== KNOWLEDGE EXTRACTION (Async, Triggered by Actions) =====
async def _trigger_knowledge_extraction(action_id):
    """
    Triggered when action has extract_knowledge=true

    Flow:
    1. Load action from database (includes title, description, keywords)
    2. Load screenshot thumbnails as base64
    3. Call KnowledgeAgent.extract_knowledge_from_action()
    4. LLM sees screenshots + action context (~5k tokens)
    5. Extract and save knowledge items
    """
    if knowledge_agent:
        await knowledge_agent.extract_knowledge_from_action(action_id)
    else:
        # Will be picked up by periodic catchup (every 5 minutes)
        logger.debug(f"KnowledgeAgent not available for {action_id}")

# ===== TOKEN USAGE COMPARISON =====
# OLD ARCHITECTURE:
# - ActionAgent: 20 screenshots × 800 tokens = 16,000 tokens
# - KnowledgeAgent: 6 screenshots × 800 tokens = 4,800 tokens
# - Total: ~20,800 tokens per cycle
#
# NEW ARCHITECTURE:
# - RawAgent: 20 screenshots × 800 tokens = 16,000 tokens (ONE TIME)
# - RawAgent output: ~4,000 tokens (scene descriptions, text)
# - ActionAgent: ~4,000 tokens (text-only, NO IMAGES)
# - KnowledgeAgent: ~5,000 tokens (action + 6 screenshots)
# - Total first cycle: ~25,000 tokens
# - If both action + knowledge from scenes: ~24,000 tokens
#
# SAVINGS:
# - Action extraction: 16k → 4k tokens (75% reduction)
# - Reusability: Same scenes can generate both actions and knowledge
# - Consistency: Both agents work from identical scene understanding

# ===== ACTIVITY MERGING (separate scheduled task) =====
# Runs every 10 minutes
async def _periodic_activity_summary():
    while is_running:
        await asyncio.sleep(600)  # 10 minutes

        # Load recent events and aggregate
        recent_events = db.events.get_since(minutes=10)

        # Group related events using similarity
        for event in recent_events:
            matching = find_matching_activity(event)

            if matching and should_merge(matching, event):
                # Extend existing activity
                matching.version += 1
                matching.end_time = now()
                matching.merge_event(event)
                db.activities.update(matching)
            else:
                # Create new activity
                activity = Activity(
                    id=generate_id(),
                    version=1,
                    title=event.title,
                    start_time=event.timestamp,
                    end_time=event.timestamp,
                    keywords=event.keywords,
                    description=event.description
                )
                db.activities.insert(activity)

# ===== KNOWLEDGE/TODO MERGING (separate scheduled tasks) =====
# Runs every 20 minutes
async def _periodic_knowledge_merge():
    while is_running:
        await asyncio.sleep(1200)  # 20 minutes

        # Load recent knowledge
        recent = db.knowledge.get_since(minutes=20)

        # Merge related knowledge items
        for item in recent:
            similar = find_similar_knowledge(item)
            if similar:
                # Combine descriptions
                combined = combine_knowledge(similar, item)
                db.combined_knowledge.insert(combined)

async def _periodic_todo_merge():
    while is_running:
        await asyncio.sleep(1200)  # 20 minutes

        # Load recent todos
        recent = db.todos.get_since(minutes=20)

        # Merge related todos
        for item in recent:
            similar = find_similar_todos(item)
            if similar:
                combined = combine_todos(similar, item)
                db.combined_todos.insert(combined)
```

**Key Points:**

- **Processing cycle:** 30 seconds (configurable, first iteration 100ms)
- **Screenshot threshold:** 20 screenshots trigger LLM extraction
- **LLM call:** Most expensive operation, happens ~every 4-6 seconds during active use
- **Activity merging:** Runs separately every 10 minutes (NOT during main loop)
- **Database persistence:** Each event/knowledge/todo saved immediately
- **Event emission:** Only event-created, knowledge-created, todo-created (NOT activity-created)
- **Activities:** Created/merged during the 10-minute aggregation task, not during main loop

### Consumption Layer Flow

```typescript
// Frontend React Application

// ===== 1. INITIAL LOAD =====
useEffect(() => {
  // When user opens app or changes date range
  activityStore.fetchTimelineData(dateRange)
    ↓
  const activities = await apiClient.getActivities({
    startDate: dateRange.start,
    endDate: dateRange.end
  })
    ↓
  // Returns activities with full details
  // (version, screenshots, keywords, description, etc.)
    ↓
  activityStore.setTimelineData(activities)
  activityStore.setMaxVersion(max(activity.version for activity in activities))
}, [dateRange])

// ===== 2. REAL-TIME UPDATES (Event-Driven) =====
// Listen for events emitted by backend processing pipeline
useTauriEvents({
  'event-created': (payload) => {
    // Raw event created (not an activity yet)
    // payload = { id, title, keywords, timestamp }

    // Update event store
    eventStore.addEvent(payload)

    // Note: Activities are created by the 10-minute aggregation task
    // This event will be aggregated into an activity later
  },

  'knowledge-created': (payload) => {
    // Knowledge item created
    knowledgeStore.addKnowledge(payload)

    // Will be merged during 20-minute merge task
  },

  'todo-created': (payload) => {
    // Todo item created
    todoStore.addTodo(payload)

    // Will be merged during 20-minute merge task
  },

  // Note: 'activity-created' event is NOT emitted by default!
  // Activities are only synced via incremental fetching
})

// ===== 3. INCREMENTAL SYNC (Fallback/Periodic) =====
// Periodically fetch new/updated activities since last sync
useEffect(() => {
  const syncTimer = setInterval(async () => {
    const lastVersion = activityStore.maxVersion

    // Fetch incremental updates
    const updates = await apiClient.getIncrementalActivities({
      sinceVersion: lastVersion
    })

    // Merge into store
    activityStore.mergeActivities(updates)
    activityStore.setMaxVersion(updates.maxVersion)
  }, 30000)  // Every 30 seconds

  return () => clearInterval(syncTimer)
}, [])

// ===== 4. AGENT ANALYSIS (On-Demand) =====
const handleGenerateTasks = async (activityId: string) => {
  // User clicks "Generate Tasks" button

  // Load activity details from database
  const activity = await apiClient.getActivity({ id: activityId })

  // Route to appropriate agents
  const agents = agentFactory.getAgents(activity)

  // Run agents in parallel
  const results = await Promise.all(
    agents.map(agent => agent.analyze(activity))
  )

  // Combine task recommendations
  const tasks = combineAgentResults(results)

  // Save to database
  await apiClient.saveTasks({
    activityId: activityId,
    tasks: tasks
  })

  // Update local store
  agentStore.setTasks(tasks)

  // Show recommendations UI
  setShowRecommendations(true)
}

// ===== 5. UI UPDATES =====
// Activity Timeline Display
function ActivityTimeline() {
  const { timelineData, loading } = useActivityStore()

  return (
    <StickyTimelineGroup
      items={timelineData}  // Auto-grouped by date
      getDate={(activity) => activity.startTime}
      renderItem={(activity) => (
        <ActivityCard
          activity={activity}
          onGenerateTasks={() => handleGenerateTasks(activity.id)}
        />
      )}
      emptyMessage={t('activity.noData')}
    />
  )
}

// When store updates → component re-renders with new activities
```

**Event Flow Timeline:**

```
T=0s      User starts working
          ↓
T=0.2s    Screenshot captured
T=0.4s    Screenshot captured
T=0.6s    Keyboard event recorded
...
T=4s      20 screenshots accumulated → LLM extraction triggered
          ↓
T=5s      Events/Knowledge/Todos saved to DB
          ↓
T=5.1s    'event-created' event emitted to frontend
          ↓
T=5.2s    Frontend receives and updates event store
          ↓
T=10m     Activity aggregation task runs
          ↓
T=10m     Activities created/merged, saved to DB
          ↓
T=10m+1s  Frontend incremental sync fetches new activities
          ↓
T=10m+2s  Frontend updates activity timeline display
          ↓
User sees activity appear in timeline
```

**Key Points:**

- **Event emission:** Only events/knowledge/todos emitted, NOT activities
- **Activity visibility:** Delayed until 10-minute aggregation task completes
- **Frontend sync:** Relies on incremental fetching (every 30s) for activities
- **Real-time:** Events visible immediately, activities take 10-20 minutes
- **On-demand:** Agent analysis triggered by user click, runs synchronously
- **Error handling:** If sync fails, retry automatically in next 30s window

## ⚠️ Critical Differences from Documentation

This section highlights important gaps between typical assumptions and the actual implementation:

### 1. **Processing Frequency: 30s, Not 10s**

- **Expected:** Processing triggered every 10 seconds
- **Actual:** Main loop runs every **30 seconds** (configurable)
- **First iteration:** 100ms (fast start)
- **Impact:** Activities take longer to appear (up to 10-20 minutes before aggregation)

### 2. **Activity Events NOT Emitted**

- **Expected:** `activity-created` and `activity-updated` events from backend
- **Actual:** Only `event-created`, `knowledge-created`, `todo-created` events emitted
- **Why:** Activities are created asynchronously by the 10-minute aggregation task
- **Frontend consequence:** Must use incremental sync to fetch new activities
- **Code location:** `backend/processing/pipeline.py` - activity creation happens in `_periodic_activity_summary()`, not in main processing loop

### 3. **Activities Created in Separate Scheduled Tasks**

- **Expected:** Activities created during main processing pipeline
- **Actual:** Activities created by **separate scheduled tasks**:
  - `_periodic_activity_summary()` - runs every 10 minutes
  - `_periodic_knowledge_merge()` - runs every 20 minutes
  - `_periodic_todo_merge()` - runs every 20 minutes
- **Impact:** Significant delay between event extraction and activity visibility

### 4. **Screenshot Threshold Triggers Event Extraction**

- **Expected:** Fixed time interval triggers LLM extraction
- **Actual:** **20 screenshots accumulated** triggers extraction
- **Duration:** ~4 seconds of normal usage (0.2s × 20)
- **Result:** Events created very frequently during active use (~every 4-6 seconds)
- **Code location:** `backend/processing/pipeline.py::process_raw_records()`

### 5. **Multiple Concurrent Scheduled Tasks**

- **Expected:** Single processing loop handles everything
- **Actual:** Three independent asyncio tasks:
  1. Main processing loop (30s cycle)
  2. Activity summary task (10m cycle)
  3. Knowledge/todo merge tasks (20m cycle)
- **Benefit:** Each task can run independently without blocking others
- **Challenge:** Complex async coordination needed

### 6. **Screenshot Capture: Every 0.2s (5/sec), Not 1s**

- **Expected:** 1 screenshot per second
- **Actual:** **5 screenshots per second** (0.2s interval)
- **Per-monitor deduplication:** Each monitor has separate hash tracking
- **Force save:** Even identical frames saved every 5 seconds
- **Impact:** High I/O and storage usage during continuous work

### 7. **Keyboard: ALL Events Captured**

- **Expected:** Filtered keyboard events
- **Actual:** **100% of keyboard events** recorded (no filtering at capture time)
- **Impact:** Complete keyboard activity record (useful for debugging)
- **Privacy note:** User needs to be aware all key presses are recorded

### 8. **Activity Latency: 10-20 Minutes, Not Real-Time**

- **Expected:** Activities appear immediately or within seconds
- **Actual:** Complete timeline:
  - T=0s: User starts working
  - T=4s: 20 screenshots accumulated → LLM extraction
  - T=5s: Events saved and emitted
  - T=10m: Activity aggregation runs, activity created
  - T=10m+30s: Frontend incremental sync fetches activity
  - T=10m+31s: Activity visible in UI
- **User experience:** May see individual events before activities

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
  title: '...'
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
