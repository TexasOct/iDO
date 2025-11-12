"""
Database migration SQL statements
Contains all ALTER TABLE and data migration statements
"""

# Events table migrations
CREATE_EVENTS_NEW_TABLE = """
    CREATE TABLE events_new (
        id TEXT PRIMARY KEY,
        start_time TEXT,
        end_time TEXT,
        type TEXT,
        summary TEXT,
        source_data TEXT,
        title TEXT DEFAULT '',
        description TEXT DEFAULT '',
        keywords TEXT,
        timestamp TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""

MIGRATE_EVENTS_DATA = """
    INSERT INTO events_new (
        id, start_time, end_time, type, summary, source_data,
        title, description, keywords, timestamp, created_at
    )
    SELECT
        id, start_time, end_time, type, summary, source_data,
        COALESCE(title, SUBSTR(COALESCE(summary, ''), 1, 100)),
        COALESCE(description, COALESCE(summary, '')),
        keywords, timestamp, created_at
    FROM events
"""

DROP_OLD_EVENTS_TABLE = "DROP TABLE events"

RENAME_EVENTS_TABLE = "ALTER TABLE events_new RENAME TO events"

ADD_EVENTS_TITLE_COLUMN = """
    ALTER TABLE events
    ADD COLUMN title TEXT DEFAULT ''
"""

UPDATE_EVENTS_TITLE = """
    UPDATE events
    SET title = SUBSTR(COALESCE(summary, ''), 1, 100)
    WHERE title = '' OR title IS NULL
"""

ADD_EVENTS_DESCRIPTION_COLUMN = """
    ALTER TABLE events
    ADD COLUMN description TEXT DEFAULT ''
"""

UPDATE_EVENTS_DESCRIPTION = """
    UPDATE events
    SET description = COALESCE(summary, '')
    WHERE description = '' OR description IS NULL
"""

ADD_EVENTS_KEYWORDS_COLUMN = """
    ALTER TABLE events
    ADD COLUMN keywords TEXT DEFAULT NULL
"""

ADD_EVENTS_TIMESTAMP_COLUMN = """
    ALTER TABLE events
    ADD COLUMN timestamp TEXT DEFAULT NULL
"""

UPDATE_EVENTS_TIMESTAMP = """
    UPDATE events
    SET timestamp = start_time
    WHERE timestamp IS NULL AND start_time IS NOT NULL
"""

ADD_EVENTS_DELETED_COLUMN = """
    ALTER TABLE events
    ADD COLUMN deleted BOOLEAN DEFAULT 0
"""

# Activities table migrations
CREATE_ACTIVITIES_NEW_TABLE = """
    CREATE TABLE activities_new (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        source_events TEXT,
        version INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted BOOLEAN DEFAULT 0,
        source_event_ids TEXT
    )
"""

MIGRATE_ACTIVITIES_DATA = """
    INSERT INTO activities_new (
        id, title, description, start_time, end_time, source_events,
        version, created_at, deleted, source_event_ids
    )
    SELECT
        id, COALESCE(title, SUBSTR(description, 1, 50)), description,
        start_time, end_time, source_events,
        COALESCE(version, 1), created_at,
        COALESCE(deleted, 0), source_event_ids
    FROM activities
"""

DROP_OLD_ACTIVITIES_TABLE = "DROP TABLE activities"

RENAME_ACTIVITIES_TABLE = "ALTER TABLE activities_new RENAME TO activities"

ADD_ACTIVITIES_VERSION_COLUMN = """
    ALTER TABLE activities
    ADD COLUMN version INTEGER DEFAULT 1
"""

ADD_ACTIVITIES_TITLE_COLUMN = """
    ALTER TABLE activities
    ADD COLUMN title TEXT DEFAULT ''
"""

UPDATE_ACTIVITIES_TITLE = """
    UPDATE activities
    SET title = SUBSTR(description, 1, 50)
    WHERE title = '' OR title IS NULL
"""

ADD_ACTIVITIES_DELETED_COLUMN = """
    ALTER TABLE activities
    ADD COLUMN deleted BOOLEAN DEFAULT 0
"""

ADD_ACTIVITIES_SOURCE_EVENT_IDS_COLUMN = """
    ALTER TABLE activities
    ADD COLUMN source_event_ids TEXT DEFAULT NULL
"""

UPDATE_ACTIVITIES_SOURCE_EVENT_IDS = """
    UPDATE activities
    SET source_event_ids = source_events
    WHERE source_event_ids IS NULL AND source_events IS NOT NULL
"""

# LLM models table migrations
ADD_LLM_MODELS_LAST_TEST_STATUS_COLUMN = """
    ALTER TABLE llm_models ADD COLUMN last_test_status INTEGER DEFAULT 0
"""

ADD_LLM_MODELS_LAST_TESTED_AT_COLUMN = """
    ALTER TABLE llm_models ADD COLUMN last_tested_at TEXT
"""

ADD_LLM_MODELS_LAST_TEST_ERROR_COLUMN = """
    ALTER TABLE llm_models ADD COLUMN last_test_error TEXT
"""

# Messages table migrations
ADD_MESSAGES_IMAGES_COLUMN = """
    ALTER TABLE messages ADD COLUMN images TEXT
"""
