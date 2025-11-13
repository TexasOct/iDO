# Type System Improvements

## Overview

This document describes the type system improvements made to the iDO backend to fix runtime errors and eliminate all type checker warnings.

## Problems Fixed

### 1. SettingsManager Database Attribute Errors

**Error:**
```
'DatabaseManager' object has no attribute 'get_all_settings'
```

**Root Cause:**
The `SettingsManager` was calling methods that didn't exist on the new repository-based `DatabaseManager`. It was using old method names like:
- `db.get_all_settings()` → Should be `db.settings.get_all()`
- `db.set_setting()` → Should be `db.settings.set()`
- `db.execute_query()` → Didn't exist in new architecture

**Solution:**
1. Updated all method calls to use the repository pattern: `db.settings.get_all()`, `db.settings.set()`, etc.
2. Added `execute_query()` method to `DatabaseManager` for backward compatibility with legacy code
3. Created type protocols to ensure type safety

### 2. Dashboard Manager Type Warnings

**Warnings:**
```
warning[possibly-missing-attribute]: Attribute `execute_query` may be missing on object of type `Unknown | DatabaseManager`
```

**Root Cause:**
The `DashboardManager` was using raw SQL queries via `execute_query()`, but the type system didn't know this method existed.

**Solution:**
1. Added `execute_query()` method to `DatabaseManager` for legacy compatibility
2. Created `DashboardDatabaseProtocol` to define the required interface
3. Added proper type annotation: `self.db: DashboardDatabaseProtocol = get_db()`

### 3. ChatService Type Warnings

**Warnings:**
```
warning[possibly-missing-attribute]: Attribute `insert_conversation` may be missing...
warning[possibly-missing-attribute]: Attribute `insert_message` may be missing...
```

**Root Cause:**
The `ChatService` was using old method names that didn't match the new repository pattern.

**Solution:**
1. Updated all database calls to use repositories:
   - `db.insert_conversation()` → `db.conversations.insert()`
   - `db.insert_message()` → `db.messages.insert()`
   - `db.get_messages()` → `db.messages.get_by_conversation()`
   - `db.update_conversation()` → `db.conversations.update()`
   - `db.delete_conversation()` → `db.conversations.delete()`
   - `db.get_conversation_by_id()` → `db.conversations.get_by_id()`
2. Created `ChatDatabaseProtocol` for type safety
3. Added proper type annotation: `self.db: ChatDatabaseProtocol = get_db()`

## Architecture Improvements

### Unified Protocol Definitions

Created `backend/core/protocols.py` with all type protocols in one place:

```python
# Repository Protocols
- SettingsRepositoryProtocol
- ActivitiesRepositoryProtocol
- ConversationsRepositoryProtocol
- MessagesRepositoryProtocol
- EventsRepositoryProtocol
- TodosRepositoryProtocol
- KnowledgeRepositoryProtocol
- LLMModelsRepositoryProtocol

# Database Manager Protocols
- DatabaseManagerProtocol (full interface)
- ChatDatabaseProtocol (specialized for chat service)
- DashboardDatabaseProtocol (specialized for dashboard)

# Other Protocols
- PerceptionManagerProtocol
```

**Benefits:**
1. **Single source of truth** - All protocols defined in one place
2. **No duplication** - Reusable across modules
3. **Type safety** - Catch errors at compile time instead of runtime
4. **Better IDE support** - Autocomplete and type hints work correctly
5. **No circular dependencies** - Protocols break dependency cycles

### Repository Pattern Migration

The codebase now consistently uses the repository pattern:

**Old (Direct Database Calls):**
```python
db.insert_conversation(id=..., title=...)
db.get_messages(conversation_id=...)
```

**New (Repository Pattern):**
```python
db.conversations.insert(conversation_id=..., title=...)
db.messages.get_by_conversation(conversation_id=...)
```

**Benefits:**
1. **Better organization** - Each repository handles one domain
2. **Type safety** - Clear interfaces via protocols
3. **Testability** - Easy to mock repositories
4. **Maintainability** - Changes isolated to specific repositories

### Backward Compatibility

Added legacy compatibility methods to `DatabaseManager`:

```python
def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
    """Execute raw SQL query (legacy compatibility)"""
    ...

def get_connection(self):
    """Get database connection (legacy compatibility)"""
    ...
```

This allows old code to continue working while gradually migrating to the new pattern.

## Files Modified

### Core Infrastructure
- `backend/core/protocols.py` - **NEW**: Unified protocol definitions
- `backend/core/db/__init__.py` - Added `execute_query()` method for legacy compatibility
- `backend/core/settings.py` - Updated to use `DatabaseManagerProtocol` and repository methods

### Services
- `backend/services/chat_service.py` - Migrated to repository pattern, uses `ChatDatabaseProtocol`

### Managers
- `backend/core/dashboard/manager.py` - Uses `DashboardDatabaseProtocol`

## Testing Results

### Type Checker
```bash
$ uv run ty check
All checks passed!
```

### Runtime Tests
```bash
$ python -c "from core.settings import init_settings; ..."
✓ Friendly chat settings: enabled=True, interval=1
✓ Live2D settings: enabled=True, notification_duration=3000
✓ Updated friendly chat interval to: 25
✓ Verified persisted interval: 25
=== All Tests Passed! ===
```

## Best Practices Going Forward

### 1. Always Use Protocols for Type Hints

**Bad:**
```python
def __init__(self):
    self.db = get_db()  # Type is Unknown
```

**Good:**
```python
def __init__(self):
    self.db: DatabaseManagerProtocol = get_db()  # Type is clear
```

### 2. Import Protocols from core.protocols

**Bad:**
```python
class MyProtocol(Protocol):  # Duplicated definition
    def method(self) -> None: ...
```

**Good:**
```python
from core.protocols import DatabaseManagerProtocol
```

### 3. Use Repository Pattern

**Bad:**
```python
db.execute_query("SELECT * FROM conversations WHERE id = ?", (id,))
```

**Good:**
```python
db.conversations.get_by_id(id)
```

### 4. Define New Protocols When Needed

If you need a specialized interface:

```python
# In core/protocols.py
class MyServiceDatabaseProtocol(Protocol):
    """Protocol for MyService database operations"""
    
    conversations: ConversationsRepositoryProtocol
    custom_repo: CustomRepositoryProtocol
```

## Benefits Summary

1. ✅ **Zero type warnings** - All type checks pass
2. ✅ **Zero runtime errors** - Fixed all database attribute errors
3. ✅ **Better type safety** - Catch errors at compile time
4. ✅ **Improved maintainability** - Clear interfaces and responsibilities
5. ✅ **Better IDE support** - Autocomplete and go-to-definition work correctly
6. ✅ **No breaking changes** - Legacy code continues to work
7. ✅ **Scalable architecture** - Easy to add new repositories and protocols
8. ✅ **Single source of truth** - All protocols in one place

## Migration Guide

If you're adding a new service that needs database access:

1. **Define protocol in `core/protocols.py`** (if needed):
   ```python
   class MyServiceDatabaseProtocol(Protocol):
       needed_repo: NeededRepositoryProtocol
   ```

2. **Import and use in your service**:
   ```python
   from core.db import get_db
   from core.protocols import MyServiceDatabaseProtocol
   
   class MyService:
       def __init__(self):
           self.db: MyServiceDatabaseProtocol = get_db()
   ```

3. **Use repository methods**:
   ```python
   data = self.db.needed_repo.get_all()
   ```

4. **Run type checker**:
   ```bash
   uv run ty check
   ```
