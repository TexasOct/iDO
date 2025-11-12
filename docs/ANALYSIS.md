# Rewind (iDO) System Architecture Analysis

## Executive Summary

This document provides a comprehensive analysis of how display/screen selection, settings management, perception layer, and prompt configuration are implemented in the iDO system.

---

## 1. Display/Screen Selection Implementation

### 1.1 Backend (Python) Implementation

#### Handler: Screen Management
**File:** `/Users/icyfeather/Projects/Rewind/backend/handlers/screens.py`

The backend provides four API handlers for screen management:

```python
@api_handler()
async def get_monitors() -> Dict[str, Any]:
    """Enumerate all connected monitors using mss library
    Returns: List of MonitorInfo with index, name, resolution, position, is_primary"""

@api_handler()
async def get_screen_settings() -> Dict[str, Any]:
    """Retrieve saved screen capture settings from config
    Returns: Current screen_settings list from settings.get()"""

@api_handler()
async def capture_all_previews() -> Dict[str, Any]:
    """Capture thumbnail previews for all monitors
    Returns: Base64-encoded JPEG previews for each monitor"""

@api_handler()
async def update_screen_settings(body: Dict[str, Any]) -> Dict[str, Any]:
    """Save user's screen selection choices
    Normalizes and stores screens list via settings.set()"""
```

**Key Implementation Details:**

- Uses `mss` library for cross-platform monitor enumeration (`mss.monitors[1:]` skips virtual bounding box)
- Generates synthetic names: "Display 1", "Display 2", etc. (mss doesn't provide monitor names)
- Captures previews by downscaling to 240px height, converting to JPEG (quality=70)
- Stores settings via `get_settings().set("screenshot.screen_settings", normalized)`

**Data Structure:**
```python
monitors = [
    {
        "index": 1,
        "name": "Display 1",
        "width": 1920,
        "height": 1080,
        "left": 0,
        "top": 0,
        "is_primary": True,
        "resolution": "1920x1080"
    }
]

screen_settings = [
    {
        "monitor_index": 1,
        "monitor_name": "Display 1",
        "is_enabled": True,
        "resolution": "1920x1080",
        "is_primary": True
    }
]
```

#### Perception Layer Integration
**File:** `/Users/icyfeather/Projects/Rewind/backend/perception/screenshot_capture.py`

The `ScreenshotCapture` class reads enabled monitors from settings and captures only enabled ones:

```python
def _get_enabled_monitor_indices(self) -> List[int]:
    """
    Load enabled monitor indices from settings.
    Returns:
    - If screen settings exist and some enabled: list of enabled indices
    - If screen settings exist but none enabled: empty list (respect user choice)
    - If no screen settings or read fails: [1] (primary monitor default)
    """
    try:
        settings = get_settings()
        screens = settings.get("screenshot.screen_settings", None)
        if not isinstance(screens, list) or len(screens) == 0:
            return [1]  # Default to primary
        enabled = [int(s.get("monitor_index")) for s in screens if s.get("is_enabled")]
        return enabled
    except Exception as e:
        logger.warning(f"Failed to read screen settings, fallback to primary: {e}")
        return [1]

def capture(self) -> Optional[RawRecord]:
    """Capture screenshots for enabled monitors only
    - Reads enabled_indices from settings
    - For each enabled monitor, calls _capture_one_monitor(sct, idx)
    - Emits callback for each monitor capture"""
```

### 1.2 Frontend (React/TypeScript) Implementation

#### Client Interface
**File:** `/Users/icyfeather/Projects/Rewind/src/lib/client/screens.ts`

Simple PyTauri wrapper functions:
```typescript
export async function getMonitors()
export async function getScreenSettings()
export async function updateScreenSettings(body: { screens: any[] })
export async function captureAllPreviews()
```

#### Settings Component
**File:** `/Users/icyfeather/Projects/Rewind/src/components/settings/ScreenSelectionSettings.tsx`

**Component Features:**
1. Load monitors and saved settings on mount
2. Capture previews for all monitors
3. Toggle individual monitors on/off
4. Save/Reset (to primary only) selections

**Key Logic:**
```typescript
const handleScreenToggle = (monitorIndex: number, enabled: boolean) => {
    // Updates local state
    // Creates new ScreenSetting if not exists
}

const handleSaveScreenSettings = async () => {
    // Ensures all monitors have settings (defaults to primary for unconfigured)
    // Calls updateScreenSettings API
    // Updates local state on success
}

const handleResetScreenSettings = async () => {
    // Sets all monitors to defaults (only primary enabled)
    // Calls updateScreenSettings API
}
```

**Frontend Data Structure:**
```typescript
interface MonitorInfo {
  index: number
  name: string
  width: number
  height: number
  left: number
  top: number
  is_primary: boolean
  resolution: string
}

interface ScreenSetting {
  id?: number
  monitor_index: number
  monitor_name: string
  is_enabled: boolean
  resolution: string
  is_primary: boolean
  created_at?: string
  updated_at?: string
}
```

---

## 2. Settings Structure & Management

### 2.1 Database Schema

**File:** `/Users/icyfeather/Projects/Rewind/backend/core/db.py`

Settings table structure:
```sql
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    type TEXT NOT NULL,           -- 'bool', 'int', 'json', 'string'
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### 2.2 Settings Manager

**File:** `/Users/icyfeather/Projects/Rewind/backend/core/settings.py`

`SettingsManager` class provides:

**Initialization:**
```python
def __init__(self, config_loader=None, db_manager=None)
def initialize(self, config_loader, db_manager=None)
```

**Core Methods:**

1. **TOML to Database Migration (One-time)**
   ```python
   def _migrate_toml_to_db(self):
       """Migrates friendly_chat and live2d settings from TOML to database on first init"""
   ```

2. **Dictionary-based Persistence**
   ```python
   def _save_dict_to_db(self, prefix: str, data: Dict[str, Any]):
       """Saves dict as prefixed keys: "friendly_chat.enabled", "friendly_chat.interval", etc."""

   def _load_dict_from_db(self, prefix: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
       """Loads dict from database with type conversion (bool, int, json)"""
   ```

3. **Feature-Specific Settings**

   **LLM Settings:**
   ```python
   def get_llm_settings() -> Dict[str, Any]
   def set_llm_settings(provider, api_key, model, base_url) -> bool
   ```
   Source: `config.toml` (not database)

   **Screenshot Settings:**
   ```python
   def get_screenshot_path() -> str
   def set_screenshot_path(path: str) -> bool
   ```
   Source: `config.toml`

   **Live2D Settings (Database-backed):**
   ```python
   def get_live2d_settings() -> Dict[str, Any]
   def update_live2d_settings(updates: Dict[str, Any]) -> Dict[str, Any]
   ```
   Structure:
   ```python
   {
       "enabled": False,
       "selected_model_url": "https://...",
       "model_dir": "",
       "remote_models": ["url1", "url2"],
       "notification_duration": 5000  # ms
   }
   ```

   **Friendly Chat Settings (Database-backed):**
   ```python
   def get_friendly_chat_settings() -> Dict[str, Any]
   def update_friendly_chat_settings(updates: Dict[str, Any]) -> Dict[str, Any]
   ```
   Structure:
   ```python
   {
       "enabled": False,
       "interval": 20,  # minutes
       "data_window": 20,  # minutes
       "enable_system_notification": True,
       "enable_live2d_display": True
   }
   ```

   **Image Optimization (TOML-backed):**
   ```python
   def get_image_optimization_config() -> Dict[str, Any]
   def set_image_optimization_config(config: Dict[str, Any]) -> bool
   ```

   **Image Compression (TOML-backed):**
   ```python
   def get_image_compression_config() -> Dict[str, Any]
   def set_image_compression_config(config: Dict[str, Any]) -> bool
   ```

### 2.3 Settings Type Definitions

**File:** `/Users/icyfeather/Projects/Rewind/src/lib/types/settings.ts`

```typescript
export interface DatabaseSettings {
  path?: string
}

export interface ScreenshotSettings {
  savePath?: string
}

export interface ScreenSetting {
  id?: number
  monitor_index: number
  monitor_name: string
  is_enabled: boolean
  resolution: string
  is_primary: boolean
  created_at?: string
  updated_at?: string
}

export interface FriendlyChatSettings {
  enabled: boolean
  interval: number  // 5-120 minutes
  dataWindow: number
  enableSystemNotification: boolean
  enableLive2dDisplay: boolean
}

export interface AppSettings {
  database?: DatabaseSettings
  screenshot?: ScreenshotSettings
  theme: 'light' | 'dark' | 'system'
  language: 'zh-CN' | 'en-US'
  friendlyChat?: FriendlyChatSettings
}
```

### 2.4 Settings Store (Frontend)

**File:** `/Users/icyfeather/Projects/Rewind/src/lib/stores/settings.ts`

Zustand store with persistence:
```typescript
interface SettingsState {
  settings: AppSettings
  loading: boolean
  error: string | null

  // Actions
  fetchSettings: () => Promise<void>
  updateDatabaseSettings: (database: Partial<DatabaseSettings>) => Promise<void>
  updateScreenshotSettings: (screenshot: Partial<ScreenshotSettings>) => Promise<void>
  updateTheme: (theme: 'light' | 'dark' | 'system') => void
  updateLanguage: (language: 'zh-CN' | 'en-US') => void
}
```

---

## 3. Perception Manager Architecture

### 3.1 Perception Manager Core

**File:** `/Users/icyfeather/Projects/Rewind/backend/perception/manager.py`

**Class:** `PerceptionManager`

**Initialization:**
```python
def __init__(
    self,
    capture_interval: float = 1.0,      # seconds
    window_size: int = 20,              # seconds (sliding window)
    on_data_captured: Optional[Callable[[RawRecord], None]] = None
)
```

**Components:**

1. **Platform-Specific Capturers**
   - `keyboard_capture`: Created via `create_keyboard_monitor(callback)`
   - `mouse_capture`: Created via `create_mouse_monitor(callback)`
   - `screenshot_capture`: `ScreenshotCapture(callback)`
   - `screen_state_monitor`: Monitors screen lock/wake events

2. **Storage**
   - `storage: SlidingWindowStorage(window_size)` - Maintains 20-second window
   - `event_buffer: EventBuffer()` - Buffers events for processing

3. **Lifecycle Methods**
   ```python
   async def start() -> None
       # Starts screen state monitor, keyboard, mouse, screenshot capturers
       # Creates async tasks: screenshot_task, cleanup_task

   async def stop() -> None
       # Stops all capturers and cancels async tasks

   async def _screenshot_loop() -> None
       # Periodically calls capture_with_interval in thread pool

   async def _cleanup_loop() -> None
       # Cleanup every 30s initially, then every 60s
       # Calls storage._cleanup_expired_records()
   ```

**Callback Methods:**
```python
def _on_keyboard_event(self, record: RawRecord) -> None
    # Stores in storage and event_buffer
    # Calls on_data_captured callback if set

def _on_mouse_event(self, record: RawRecord) -> None
    # Only important mouse events (via is_important_event check)

def _on_screenshot_event(self, record: RawRecord) -> None
    # Stores non-duplicate screenshots

def _on_screen_lock(self) -> None
    # Pauses all capturers when screen locks

def _on_screen_unlock(self) -> None
    # Resumes all capturers when screen wakes
```

**Data Retrieval Methods:**
```python
def get_recent_records(self, count: int = 100) -> list
def get_records_by_type(self, event_type: str) -> list
def get_records_in_timeframe(self, start_time: datetime, end_time: datetime) -> list
def get_records_in_last_n_seconds(self, seconds: int) -> list
def get_buffered_events(self) -> list
def get_stats(self) -> Dict[str, Any]
```

### 3.2 Keyboard & Mouse Monitoring

**Platform-Specific Implementations:**
- macOS: `/Users/icyfeather/Projects/Rewind/backend/perception/platforms/macos/keyboard.py`
- macOS: `/Users/icyfeather/Projects/Rewind/backend/perception/platforms/macos/mouse.py`
- Windows: `/Users/icyfeather/Projects/Rewind/backend/perception/platforms/windows/keyboard.py`
- Windows: `/Users/icyfeather/Projects/Rewind/backend/perception/platforms/windows/mouse.py`
- Linux: `/Users/icyfeather/Projects/Rewind/backend/perception/platforms/linux/keyboard.py`
- Linux: `/Users/icyfeather/Projects/Rewind/backend/perception/platforms/linux/mouse.py`

All implement:
```python
class KeyboardCapture(BaseCapture):
    def start() -> None
    def stop() -> None
    def get_stats() -> Dict[str, Any]

class MouseCapture(BaseCapture):
    def start() -> None
    def stop() -> None
    def is_important_event(data: Dict) -> bool
    def get_stats() -> Dict[str, Any]
```

### 3.3 Screenshot Capture

**File:** `/Users/icyfeather/Projects/Rewind/backend/perception/screenshot_capture.py`

**Key Features:**

1. **Per-Monitor Deduplication**
   ```python
   self._last_hashes: Dict[int, Optional[str]] = {}  # Track last hash per monitor
   ```

2. **Enabled Monitor Selection**
   ```python
   def _get_enabled_monitor_indices(self) -> List[int]:
       # Returns from settings.get("screenshot.screen_settings")
       # Defaults to [1] if not configured
   ```

3. **Screenshot Processing**
   ```python
   def _capture_one_monitor(self, sct: MSSBase, monitor_index: int):
       # Grabs monitor screenshot
       # Converts BGRA to RGB with PIL
       # Applies image processing
       # Calculates perceptual hash
       # Checks for duplicates
       # Stores in image_manager cache
       # Emits callback
   ```

4. **Compression Settings**
   ```python
   def set_compression_settings(self, quality: int = 85, max_width: int = 1920, max_height: int = 1080)
   ```

### 3.4 Coordinator Integration

**File:** `/Users/icyfeather/Projects/Rewind/backend/core/coordinator.py`

**PipelineCoordinator** manages perception lifecycle:

```python
class PipelineCoordinator:
    def __init__(self, config: Dict[str, Any]):
        self.perception_manager = None  # Lazy initialized
        self.processing_pipeline = None
        self.is_running = False
        self.mode = "stopped"  # running | stopped | requires_model | error | starting

    def _init_managers(self):
        from perception.manager import PerceptionManager
        self.perception_manager = PerceptionManager(
            capture_interval=self.capture_interval,
            window_size=self.window_size
        )
```

**Perception Settings from Config:**
```toml
[monitoring]
capture_interval = 1         # seconds
window_size = 60            # seconds
processing_interval = 30    # seconds
```

---

## 4. Prompts Configuration & Event Extraction

### 4.1 Prompts Configuration Files

**English Prompts:** `/Users/icyfeather/Projects/Rewind/backend/config/prompts_en.toml`
**Chinese Prompts:** `/Users/icyfeather/Projects/Rewind/backend/config/prompts_zh.toml`

### 4.2 Event Extraction Configuration

**Section:** `[prompts.event_extraction]`

**Structure:**
```toml
[prompts.event_extraction]
system_prompt = """
Comprehensive instructions for extracting events from screenshots.
Instructions for:
- Event titles (format: [App] — [Action] [Object] ([Context]))
- Event descriptions (must include 5+ details)
- Knowledge extraction (principles, mechanisms, reusable concepts)
- To-do extraction (explicit, executable tasks)
...
"""

user_prompt_template = """
Template for user input processing.
Includes: {input_usage_hint} placeholder for keyboard/mouse hints
Specifies: JSON output format with events, knowledge, todos arrays
"""

[config.event_extraction]
max_tokens = 4000
temperature = 0.7
```

**Event Output Format:**
```python
{
    "events": [
        {
            "title": "string",
            "description": "string",
            "keywords": ["string"],  # ≤5 high-distinctiveness tags
            "image_index": [0, 1, 2]  # 1-3 key screenshots
        }
    ],
    "knowledge": [
        {
            "title": "string",
            "description": "string",
            "keywords": ["string"]
        }
    ],
    "todos": [
        {
            "title": "string",
            "description": "string",
            "keywords": ["string"]
        }
    ]
}
```

### 4.3 Additional Prompt Configurations

1. **Activity Aggregation** (`[prompts.activity_aggregation]`)
   - Merges events into higher-level activities
   - Criteria: same object + same goal + continuous progression
   - Config: `max_tokens = 4000`, `temperature = 0.5`

2. **Knowledge Merge** (`[prompts.knowledge_merge]`)
   - Deduplicates and merges related knowledge entries
   - Config: `max_tokens = 8000`, `temperature = 0.5`

3. **Todo Merge** (`[prompts.todo_merge]`)
   - Aggregates related todo items
   - Config: `max_tokens = 8000`, `temperature = 0.5`

4. **Diary Generation** (`[prompts.diary_generation]`)
   - Generates personal diary entries from activities
   - Config: `max_tokens = 4000`, `temperature = 0.8`

5. **Friendly Chat** (`[prompts.friendly_chat]`)
   - Generates friendly chat messages based on activities
   - Config: `max_tokens = 150`, `temperature = 0.9`

### 4.4 Processing Configuration

**File:** `/Users/icyfeather/Projects/Rewind/backend/config/config.toml`

```toml
[processing]
# Event extraction
event_extraction_threshold = 20  # Trigger after 20 screenshots
min_screenshots_per_event = 2

# Activity aggregation
activity_summary_interval = 600  # 10 minutes
enable_auto_activity_summary = true

# Knowledge and todo merging
knowledge_merge_interval = 1200  # 20 minutes
todo_merge_interval = 1200      # 20 minutes
enable_auto_merge = true
```

---

## 5. Perception Settings Storage & Loading

### 5.1 Settings Storage Hierarchy

**Priority Order:**
1. **Database (Runtime)** - `SettingsManager` with database backend for mutable settings
2. **TOML Config** - `config.toml` for static/deployment settings
3. **Defaults** - Built-in defaults if neither above exists

### 5.2 Perception-Related Settings

**Screenshot Settings (stored in settings table):**
```python
settings.get("screenshot.screen_settings")  # List of ScreenSetting dicts
```

**Image Optimization (config.toml):**
```toml
[image_optimization]
enabled = true
strategy = "hybrid"                    # none | sampling | content_aware | hybrid
phash_threshold = 0.15                 # 0.0-1.0
min_sampling_interval = 2.0            # seconds
max_images_per_event = 8               # hard limit
enable_content_analysis = true
enable_text_detection = false          # experimental
compression_level = "aggressive"       # ultra | aggressive | balanced | quality
enable_region_cropping = false
crop_threshold = 30                    # pixel brightness difference
memory_cache_size = 500                # base64 cache entries
```

**Monitoring Configuration (config.toml):**
```toml
[monitoring]
capture_interval = 1        # seconds
window_size = 60           # seconds (sliding window)
processing_interval = 30   # seconds
```

### 5.3 Settings Loading Flow

```
SettingsManager.initialize(config_loader, db_manager)
├── Load config_loader (TOML files)
├── Load db_manager (SQLite)
├── Call _migrate_toml_to_db()  # One-time migration
│   ├── Check if DB has settings
│   └── Migrate friendly_chat and live2d from TOML to DB
└── Emit initialization log
```

**For Perception Specifically:**

```
ScreenshotCapture._get_enabled_monitor_indices()
├── get_settings().get("screenshot.screen_settings", None)
├── If not list or empty: return [1] (primary)
└── If list: return [int(s["monitor_index"]) for s in screens if s["is_enabled"]]

ScreenshotCapture.set_compression_settings(quality, max_width, max_height)
├── Store in instance variables
└── Used during image processing
```

---

## 6. Handler & API Integration

### 6.1 Perception Handlers

**File:** `/Users/icyfeather/Projects/Rewind/backend/handlers/perception.py`

API Handlers:
```python
@api_handler()
async def get_perception_stats() -> Dict[str, Any]
    # Returns: is_running, storage stats, keyboard/mouse/screenshot stats, buffer size

@api_handler(body=GetRecordsRequest)
async def get_records(body: GetRecordsRequest) -> Dict[str, Any]
    # Filters by event_type or timeframe
    # Returns: list of records with timestamp, type, data

@api_handler()
async def start_perception() -> Dict[str, Any]

@api_handler()
async def stop_perception() -> Dict[str, Any]

@api_handler()
async def clear_records() -> Dict[str, Any]

@api_handler()
async def get_buffered_events() -> Dict[str, Any]
```

### 6.2 Screen Handlers

**File:** `/Users/icyfeather/Projects/Rewind/backend/handlers/screens.py`

API Handlers:
```python
@api_handler()
async def get_monitors() -> Dict[str, Any]

@api_handler()
async def get_screen_settings() -> Dict[str, Any]

@api_handler()
async def capture_all_previews() -> Dict[str, Any]

@api_handler()
async def update_screen_settings(body: Dict[str, Any]) -> Dict[str, Any]
```

---

## 7. Data Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│              Frontend (React/TypeScript)              │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ScreenSelectionSettings Component                  │
│  ├── calls getMonitors()                            │
│  ├── calls getScreenSettings()                      │
│  ├── calls captureAllPreviews()                     │
│  └── calls updateScreenSettings()                  │
│                                                       │
└──────────────────┬──────────────────────────────────┘
                   │ PyTauri/FastAPI
                   ↓
┌─────────────────────────────────────────────────────┐
│         Backend Python (Handlers & API)               │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ScreensHandler (screens.py)                        │
│  ├── get_monitors() → mss.enumerate()              │
│  ├── get_screen_settings() → settings.get()        │
│  ├── capture_all_previews() → mss.grab()           │
│  └── update_screen_settings() → settings.set()     │
│                                                       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│    SettingsManager & Database                        │
├─────────────────────────────────────────────────────┤
│                                                       │
│  settings.get("screenshot.screen_settings")        │
│  ├── reads from SQLite settings table OR            │
│  ├── reads from TOML config.toml                   │
│  └── applies defaults if neither exist             │
│                                                       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│    Perception Manager                                │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ScreenshotCapture                                  │
│  ├── _get_enabled_monitor_indices()                │
│  ├── capture() [for each enabled monitor]          │
│  ├── _capture_one_monitor()                        │
│  ├── [deduplication, hashing, processing]         │
│  └── emit callback with RawRecord                  │
│                                                       │
│  KeyboardCapture, MouseCapture                     │
│  ScreenStateMonitor                                │
│                                                       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
         ┌─────────────────┐
         │  RawRecords    │
         │  Storage       │
         │  (20s window)  │
         └─────────────────┘
```

---

## 8. Key Files Summary

| File | Purpose |
|------|---------|
| `/backend/handlers/screens.py` | Screen selection APIs |
| `/backend/handlers/perception.py` | Perception control APIs |
| `/backend/core/settings.py` | Settings management & persistence |
| `/backend/core/db.py` | SQLite database schema & operations |
| `/backend/perception/manager.py` | Perception layer coordinator |
| `/backend/perception/screenshot_capture.py` | Screenshot capture with deduplication |
| `/backend/perception/platforms/*/keyboard.py` | Platform-specific keyboard monitoring |
| `/backend/perception/platforms/*/mouse.py` | Platform-specific mouse monitoring |
| `/backend/config/config.toml` | System configuration (monitoring, processing) |
| `/backend/config/prompts_en.toml` | English LLM prompts |
| `/backend/config/prompts_zh.toml` | Chinese LLM prompts |
| `/src/components/settings/ScreenSelectionSettings.tsx` | Frontend screen selection UI |
| `/src/lib/client/screens.ts` | Frontend API client for screens |
| `/src/lib/types/settings.ts` | Frontend TypeScript type definitions |
| `/src/lib/stores/settings.ts` | Frontend Zustand settings store |

---

## 9. Key Architectural Patterns

### 9.1 Settings Hierarchy Pattern
- **Dynamic (Database):** User settings modified at runtime (friendly_chat, live2d, screen_settings)
- **Static (TOML):** Deployment/configuration settings (monitoring, image_optimization, prompts)
- **Defaults:** Built-in defaults for any missing configuration

### 9.2 Perception Factory Pattern
Platform-specific implementations created at runtime:
```python
create_keyboard_monitor(callback)  # Returns macOS/Windows/Linux implementation
create_mouse_monitor(callback)
create_screen_state_monitor(on_lock, on_unlock)
```

### 9.3 API Handler Pattern
Single handler definition works for both PyTauri (desktop) and FastAPI (web):
```python
@api_handler()
async def handler() -> Dict[str, Any]:
    # Auto-generates TypeScript client
    # Auto-converts snake_case ↔ camelCase
    # Works in both PyTauri and FastAPI
```

### 9.4 Sliding Window Storage
```
Timeline: [Old records] ← 20s window → [Recent records]
          └─ Auto-cleanup ─┘              └─ Kept ─┘
```

---

## 10. Configuration Defaults

### Default Perception Settings
```python
# ScreenshotCapture
compression_quality = 85
max_width = 1920
max_height = 1080
enable_phash = True
force_save_interval = 5.0  # seconds

# PerceptionManager
capture_interval = 1.0  # seconds
window_size = 20       # seconds (from coordinator: 60 seconds)

# Enabled monitors
Default: [1] (primary monitor only)
When configured: Uses screenshot.screen_settings from database
```

### Default Image Optimization
```toml
strategy = "hybrid"
phash_threshold = 0.15      # Moderate aggressiveness
min_sampling_interval = 2.0 # seconds
max_images_per_event = 8
compression_level = "aggressive"
enable_region_cropping = false
```

---

## 11. Important Notes

1. **Screen Settings Storage:**
   - Stored in SQLite `settings` table with keys like `"screenshot.screen_settings"`
   - Type is `"json"` for the array of screen objects
   - Falls back to `[1]` (primary monitor) if not configured

2. **Deduplication:**
   - Per-monitor hash tracking prevents duplicate screenshots
   - Force-save every 5 seconds to catch important unchanged states
   - Uses perceptual hashing for image similarity detection

3. **Pause on Screen Lock:**
   - All capturers pause when screen locks
   - Resume when screen wakes
   - Useful for privacy and battery optimization

4. **Prompts are Multilingual:**
   - English: `prompts_en.toml`
   - Chinese: `prompts_zh.toml`
   - Language selected by `language.default_language` in `config.toml`

5. **Settings Manager Initialization:**
   - One-time TOML→Database migration on first init
   - Subsequent loads from database for mutable settings
   - TOML still used for static configuration

---

## Appendix: Related Components

- **Image Manager:** Handles image caching and optimization (`processing/image_manager.py`)
- **Database Manager:** Handles SQLite operations (`core/db.py`)
- **Logger:** Centralized logging (`core/logger.py`)
- **Paths Manager:** Unified directory structure (`core/paths.py`)
- **Config Loader:** TOML file loading (`config/loader.py`)

