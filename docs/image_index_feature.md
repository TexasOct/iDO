# Image Index Feature for Event Extraction

## Overview

This feature enhances the event extraction process by allowing the LLM to selectively choose which screenshots are most relevant to each event. Instead of saving all 20 screenshots for every event, the LLM can now specify an `image_index` array indicating which screenshots (0-19) are core to that particular event.

## Motivation

When processing 20 screenshots, not all of them are equally relevant to every extracted event. Some screenshots may be:
- Repetitive (showing nearly identical content)
- Less relevant to a specific event
- Related to different events entirely

By allowing the LLM to filter screenshots per event, we can:
1. **Reduce storage**: Only save relevant screenshots for each event
2. **Improve context**: Each event has its most pertinent visual evidence
3. **Better organization**: Events are linked to their actual visual context

## Implementation

### 1. Prompt Template Changes

**Chinese Prompt** (`backend/config/prompts_zh.toml`):
```json
{
    "events": [
        {
            "title": "string",
            "description": "string",
            "keywords": ["string"],
            "image_index": [0, 1, 5] // Core related screenshot indexes (0-19)
        }
    ]
}
```

**English Prompt** (`backend/config/prompts_en.toml`):
```json
{
    "events": [
        {
            "title": "string",
            "description": "string",
            "keywords": ["string"],
            "image_index": [0, 1, 5] // Core related screenshot indexes (0-19)
        }
    ]
}
```

### 2. Backend Logic Changes

**File**: `backend/processing/pipeline.py`

#### Modified Method: `_resolve_event_screenshot_hashes`

**Before**:
```python
def _resolve_event_screenshot_hashes(
    self, event_data: Dict[str, Any], default_hashes: List[str]
) -> List[str]:
    """Prefer screenshot info provided by the event itself"""
    # Simple fallback to default hashes
```

**After**:
```python
def _resolve_event_screenshot_hashes(
    self, event_data: Dict[str, Any], records: List[RawRecord]
) -> List[str]:
    """
    Resolve screenshot hashes based on image_index from LLM response
    
    - Reads image_index (or imageIndex) from event data
    - Filters screenshot records by index
    - Returns corresponding screenshot hashes
    - Falls back to first 6 screenshots if image_index not provided
    """
```

### 3. Key Features

1. **Flexible Index Support**: Accepts both `image_index` (snake_case) and `imageIndex` (camelCase)
2. **Range Validation**: Only accepts indices 0-19 (matching the 20 screenshots)
3. **Deduplication**: Automatically removes duplicate indices
4. **Limit Enforcement**: Maximum 6 screenshots per event
5. **Graceful Fallback**: Uses first 6 screenshots if no valid `image_index` provided
6. **Error Handling**: Logs warnings for invalid indices but continues processing

## Usage Example

### LLM Response

```json
{
    "events": [
        {
            "title": "Coding Python function",
            "description": "Writing a new data processing function in VS Code",
            "keywords": ["coding", "python", "vscode"],
            "image_index": [2, 5, 8]  // Only screenshots 2, 5, and 8 are relevant
        },
        {
            "title": "Reading documentation",
            "description": "Reading Python documentation for pandas library",
            "keywords": ["documentation", "pandas", "learning"],
            "image_index": [10, 11, 12, 13]  // Screenshots 10-13 show docs
        }
    ]
}
```

### Processing Result

- **Event 1** will be linked to screenshot hashes at indices [2, 5, 8]
- **Event 2** will be linked to screenshot hashes at indices [10, 11, 12, 13]
- Each event has only its relevant screenshots, not all 20

## Testing

A comprehensive test suite validates:

1. ✅ Specific image_index filtering
2. ✅ CamelCase imageIndex support
3. ✅ Fallback when no image_index provided
4. ✅ Deduplication of duplicate indices
5. ✅ Out-of-range index handling
6. ✅ Limit to 6 screenshots per event

All tests pass successfully.

## Benefits

1. **Storage Efficiency**: Only relevant screenshots stored per event
2. **Better Context**: Events linked to their actual visual evidence
3. **LLM Intelligence**: Leverages LLM's understanding to filter redundant screenshots
4. **Backward Compatible**: Falls back gracefully if image_index not provided

## Migration Notes

- **No database changes required**: Uses existing `screenshot_hashes` field
- **No breaking changes**: Existing events without image_index continue to work
- **Immediate effect**: New events will use filtered screenshots as soon as LLM provides image_index

## Future Enhancements

Potential improvements:
1. Allow LLM to provide confidence scores for each image_index
2. Enable screenshot reordering based on relevance
3. Support cross-event screenshot sharing (same screenshot used by multiple events)
4. Add analytics on screenshot utilization rates
