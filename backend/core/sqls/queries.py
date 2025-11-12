"""
Database query SQL statements
Contains all SELECT, INSERT, UPDATE, DELETE statements
"""

# Raw records queries
INSERT_RAW_RECORD = """
    INSERT INTO raw_records (timestamp, type, data)
    VALUES (?, ?, ?)
"""

SELECT_RAW_RECORDS = """
    SELECT * FROM raw_records
    ORDER BY timestamp DESC
    LIMIT ? OFFSET ?
"""

# Events queries
INSERT_EVENT = """
    INSERT INTO events (id, start_time, end_time, type, summary, source_data)
    VALUES (?, ?, ?, ?, ?, ?)
"""

SELECT_EVENTS = """
    SELECT * FROM events
    ORDER BY start_time DESC
    LIMIT ? OFFSET ?
"""

# Activities queries
INSERT_ACTIVITY = """
    INSERT INTO activities (id, title, description, start_time, end_time, source_events)
    VALUES (?, ?, ?, ?, ?, ?)
"""

DELETE_ACTIVITY = """
    DELETE FROM activities
    WHERE id = ?
"""

SELECT_ACTIVITIES = """
    SELECT * FROM activities
    ORDER BY start_time DESC
    LIMIT ? OFFSET ?
"""

SELECT_MAX_ACTIVITY_VERSION = """
    SELECT MAX(version) as max_version FROM activities
"""

SELECT_ACTIVITIES_AFTER_VERSION = """
    SELECT * FROM activities
    WHERE version > ?
    ORDER BY version DESC, start_time DESC
    LIMIT ?
"""

SELECT_ACTIVITY_COUNT_BY_DATE = """
    SELECT
        DATE(start_time) as date,
        COUNT(*) as count
    FROM activities
    WHERE deleted = 0
    GROUP BY DATE(start_time)
    ORDER BY date DESC
"""

SELECT_EVENT_COUNT_BY_DATE = """
    SELECT
        DATE(timestamp) as date,
        COUNT(*) as count
    FROM events
    WHERE deleted = 0
    GROUP BY DATE(timestamp)
    ORDER BY date DESC
"""

SELECT_COMBINED_KNOWLEDGE_COUNT_BY_DATE = """
    SELECT
        DATE(created_at) as date,
        COUNT(*) as count
    FROM combined_knowledge
    WHERE deleted = 0
    GROUP BY DATE(created_at)
    ORDER BY date DESC
"""

SELECT_KNOWLEDGE_COUNT_BY_DATE = """
    SELECT
        DATE(created_at) as date,
        COUNT(*) as count
    FROM knowledge
    WHERE deleted = 0
    GROUP BY DATE(created_at)
    ORDER BY date DESC
"""

# Tasks queries
INSERT_TASK = """
    INSERT INTO tasks (id, title, description, status, agent_type, parameters)
    VALUES (?, ?, ?, ?, ?, ?)
"""

UPDATE_TASK_STATUS = """
    UPDATE tasks
    SET status = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
"""

SELECT_TASKS_BY_STATUS = """
    SELECT * FROM tasks
    WHERE status = ?
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
"""

SELECT_ALL_TASKS = """
    SELECT * FROM tasks
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
"""

# Settings queries
INSERT_OR_REPLACE_SETTING = """
    INSERT OR REPLACE INTO settings (key, value, type, description, updated_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
"""

SELECT_SETTING_BY_KEY = """
    SELECT value FROM settings WHERE key = ?
"""

SELECT_ALL_SETTINGS = """
    SELECT key, value, type FROM settings ORDER BY key
"""

DELETE_SETTING = """
    DELETE FROM settings WHERE key = ?
"""

# Conversations queries
INSERT_CONVERSATION = """
    INSERT INTO conversations (id, title, related_activity_ids, metadata)
    VALUES (?, ?, ?, ?)
"""

SELECT_CONVERSATIONS = """
    SELECT * FROM conversations
    ORDER BY updated_at DESC
    LIMIT ? OFFSET ?
"""

SELECT_CONVERSATION_BY_ID = """
    SELECT * FROM conversations WHERE id = ?
"""

DELETE_CONVERSATION = """
    DELETE FROM conversations WHERE id = ?
"""

# Messages queries
INSERT_MESSAGE = """
    INSERT INTO messages (id, conversation_id, role, content, timestamp, metadata, images)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""

SELECT_MESSAGES_BY_CONVERSATION = """
    SELECT * FROM messages
    WHERE conversation_id = ?
    ORDER BY timestamp ASC
    LIMIT ? OFFSET ?
"""

SELECT_MESSAGE_BY_ID = """
    SELECT * FROM messages WHERE id = ?
"""

DELETE_MESSAGE = """
    DELETE FROM messages WHERE id = ?
"""

SELECT_MESSAGE_COUNT = """
    SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?
"""

# LLM models queries
SELECT_ACTIVE_LLM_MODEL = """
    SELECT
        id,
        name,
        provider,
        api_url,
        model,
        api_key,
        input_token_price,
        output_token_price,
        currency,
        last_test_status,
        last_tested_at,
        last_test_error,
        created_at,
        updated_at
    FROM llm_models
    WHERE is_active = 1
    LIMIT 1
"""

SELECT_LLM_MODEL_BY_ID = """
    SELECT
        id,
        name,
        provider,
        api_url,
        model,
        api_key,
        input_token_price,
        output_token_price,
        currency,
        is_active,
        last_test_status,
        last_tested_at,
        last_test_error,
        created_at,
        updated_at
    FROM llm_models
    WHERE id = ?
    LIMIT 1
"""

UPDATE_MODEL_TEST_RESULT = """
    UPDATE llm_models
    SET
        last_test_status = ?,
        last_tested_at = ?,
        last_test_error = ?,
        updated_at = ?
    WHERE id = ?
"""

# Pragma queries (for table inspection)
PRAGMA_TABLE_INFO = "PRAGMA table_info({})"
