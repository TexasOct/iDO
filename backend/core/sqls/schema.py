"""
Database schema definitions
Contains all CREATE TABLE and CREATE INDEX statements
"""

# Table creation statements
CREATE_RAW_RECORDS_TABLE = """
    CREATE TABLE IF NOT EXISTS raw_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        type TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_EVENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        source_action_ids TEXT,
        aggregated_into_activity_id TEXT,
        version INTEGER DEFAULT 1,
        deleted BOOLEAN DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (aggregated_into_activity_id) REFERENCES activities(id) ON DELETE SET NULL
    )
"""

CREATE_KNOWLEDGE_TABLE = """
    CREATE TABLE IF NOT EXISTS knowledge (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        keywords TEXT,
        source_action_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted BOOLEAN DEFAULT 0,
        FOREIGN KEY (source_action_id) REFERENCES actions(id) ON DELETE SET NULL
    )
"""

CREATE_TODOS_TABLE = """
    CREATE TABLE IF NOT EXISTS todos (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        keywords TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed BOOLEAN DEFAULT 0,
        deleted BOOLEAN DEFAULT 0,
        scheduled_date TEXT,
        scheduled_time TEXT,
        scheduled_end_time TEXT,
        recurrence_rule TEXT
    )
"""

CREATE_DIARIES_TABLE = """
    CREATE TABLE IF NOT EXISTS diaries (
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL UNIQUE,
        content TEXT NOT NULL,
        source_activity_ids TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted BOOLEAN DEFAULT 0
    )
"""

CREATE_ACTIVITIES_TABLE = """
    CREATE TABLE IF NOT EXISTS activities (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        session_duration_minutes INTEGER,
        topic_tags TEXT,
        source_event_ids TEXT,
        user_merged_from_ids TEXT,
        user_split_into_ids TEXT,
        deleted BOOLEAN DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_TASKS_TABLE = """
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        agent_type TEXT,
        parameters TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_SETTINGS_TABLE = """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_CONVERSATIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        related_activity_ids TEXT,
        metadata TEXT,
        model_id TEXT
    )
"""

CREATE_MESSAGES_TABLE = """
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT,
        images TEXT,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    )
"""

CREATE_LLM_TOKEN_USAGE_TABLE = """
    CREATE TABLE IF NOT EXISTS llm_token_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        model TEXT NOT NULL,
        model_config_id TEXT,
        prompt_tokens INTEGER NOT NULL DEFAULT 0,
        completion_tokens INTEGER NOT NULL DEFAULT 0,
        total_tokens INTEGER NOT NULL DEFAULT 0,
        cost REAL DEFAULT 0.0,
        request_type TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (model_config_id) REFERENCES llm_models(id) ON DELETE SET NULL
    )
"""

CREATE_EVENT_IMAGES_TABLE = """
    CREATE TABLE IF NOT EXISTS event_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL,
        hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
        UNIQUE(event_id, hash)
    )
"""

CREATE_LLM_MODELS_TABLE = """
    CREATE TABLE IF NOT EXISTS llm_models (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        provider TEXT NOT NULL,
        api_url TEXT NOT NULL,
        model TEXT NOT NULL,
        api_key TEXT NOT NULL,
        input_token_price REAL NOT NULL DEFAULT 0.0,
        output_token_price REAL NOT NULL DEFAULT 0.0,
        currency TEXT DEFAULT 'USD',
        is_active INTEGER DEFAULT 0,
        last_test_status INTEGER DEFAULT 0,
        last_tested_at TEXT,
        last_test_error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CHECK(input_token_price >= 0),
        CHECK(output_token_price >= 0)
    )
"""

# ============ Three-Layer Architecture Tables ============
# New tables for Action → Event → Activity hierarchy

CREATE_ACTIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS actions (
        id TEXT PRIMARY KEY,
        title TEXT DEFAULT '',
        description TEXT DEFAULT '',
        keywords TEXT,
        timestamp TEXT,
        aggregated_into_event_id TEXT,
        extract_knowledge BOOLEAN DEFAULT 0,
        knowledge_extracted BOOLEAN DEFAULT 0,
        deleted BOOLEAN DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (aggregated_into_event_id) REFERENCES events(id) ON DELETE SET NULL
    )
"""

CREATE_ACTION_IMAGES_TABLE = """
    CREATE TABLE IF NOT EXISTS action_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_id TEXT NOT NULL,
        hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE,
        UNIQUE(action_id, hash)
    )
"""

CREATE_SESSION_PREFERENCES_TABLE = """
    CREATE TABLE IF NOT EXISTS session_preferences (
        id TEXT PRIMARY KEY,
        preference_type TEXT NOT NULL,
        pattern_description TEXT,
        confidence_score REAL DEFAULT 0.5,
        times_observed INTEGER DEFAULT 1,
        last_observed TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_KNOWLEDGE_CREATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_knowledge_created
    ON knowledge(created_at DESC)
"""

CREATE_KNOWLEDGE_DELETED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_knowledge_deleted
    ON knowledge(deleted)
"""

CREATE_KNOWLEDGE_SOURCE_ACTION_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_knowledge_source_action
    ON knowledge(source_action_id)
"""

CREATE_TODOS_CREATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_todos_created
    ON todos(created_at DESC)
"""

CREATE_TODOS_COMPLETED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_todos_completed
    ON todos(completed)
"""

CREATE_TODOS_DELETED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_todos_deleted
    ON todos(deleted)
"""

CREATE_DIARIES_DATE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_diaries_date
    ON diaries(date DESC)
"""

# Index creation statements
CREATE_MESSAGES_CONVERSATION_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, timestamp DESC)
"""

CREATE_CONVERSATIONS_UPDATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_conversations_updated
    ON conversations(updated_at DESC)
"""

CREATE_EVENT_IMAGES_EVENT_ID_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_event_images_event_id
    ON event_images(event_id)
"""

CREATE_EVENT_IMAGES_HASH_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_event_images_hash
    ON event_images(hash)
"""

CREATE_LLM_USAGE_TIMESTAMP_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_llm_usage_timestamp
    ON llm_token_usage(timestamp DESC)
"""

CREATE_LLM_USAGE_MODEL_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_llm_usage_model
    ON llm_token_usage(model)
"""

CREATE_LLM_USAGE_MODEL_CONFIG_ID_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_llm_usage_model_config_id
    ON llm_token_usage(model_config_id)
"""

CREATE_LLM_MODELS_PROVIDER_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_llm_models_provider
    ON llm_models(provider)
"""

CREATE_LLM_MODELS_IS_ACTIVE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_llm_models_is_active
    ON llm_models(is_active)
"""

CREATE_LLM_MODELS_CREATED_AT_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_llm_models_created_at
    ON llm_models(created_at DESC)
"""

CREATE_EVENTS_START_TIME_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_events_start_time
    ON events(start_time DESC)
"""

CREATE_EVENTS_CREATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_events_created
    ON events(created_at DESC)
"""

CREATE_EVENTS_AGGREGATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_events_aggregated
    ON events(aggregated_into_activity_id)
"""

CREATE_ACTIVITIES_START_TIME_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_activities_start_time
    ON activities(start_time DESC)
"""

CREATE_ACTIVITIES_CREATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_activities_created
    ON activities(created_at DESC)
"""

CREATE_ACTIVITIES_UPDATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_activities_updated
    ON activities(updated_at DESC)
"""

# ============ Three-Layer Architecture Indexes ============

CREATE_ACTIONS_TIMESTAMP_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_actions_timestamp
    ON actions(timestamp DESC)
"""

CREATE_ACTIONS_CREATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_actions_created
    ON actions(created_at DESC)
"""

CREATE_ACTIONS_AGGREGATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_actions_aggregated
    ON actions(aggregated_into_event_id)
"""

CREATE_ACTIONS_EXTRACT_KNOWLEDGE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_actions_extract_knowledge
    ON actions(extract_knowledge, knowledge_extracted)
"""

CREATE_ACTION_IMAGES_ACTION_ID_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_action_images_action_id
    ON action_images(action_id)
"""

CREATE_ACTION_IMAGES_HASH_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_action_images_hash
    ON action_images(hash)
"""

CREATE_SESSION_PREFERENCES_TYPE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_session_preferences_type
    ON session_preferences(preference_type)
"""

CREATE_SESSION_PREFERENCES_CONFIDENCE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_session_preferences_confidence
    ON session_preferences(confidence_score DESC)
"""

# All table creation statements in order
ALL_TABLES = [
    CREATE_RAW_RECORDS_TABLE,
    CREATE_EVENTS_TABLE,
    CREATE_ACTIVITIES_TABLE,
    CREATE_KNOWLEDGE_TABLE,
    CREATE_TODOS_TABLE,
    CREATE_DIARIES_TABLE,
    CREATE_TASKS_TABLE,
    CREATE_SETTINGS_TABLE,
    CREATE_CONVERSATIONS_TABLE,
    CREATE_MESSAGES_TABLE,
    CREATE_LLM_TOKEN_USAGE_TABLE,
    CREATE_EVENT_IMAGES_TABLE,
    CREATE_LLM_MODELS_TABLE,
    # Three-layer architecture tables
    CREATE_ACTIONS_TABLE,
    CREATE_ACTION_IMAGES_TABLE,
    CREATE_SESSION_PREFERENCES_TABLE,
]

# All index creation statements
ALL_INDEXES = [
    CREATE_MESSAGES_CONVERSATION_INDEX,
    CREATE_CONVERSATIONS_UPDATED_INDEX,
    CREATE_EVENT_IMAGES_EVENT_ID_INDEX,
    CREATE_EVENT_IMAGES_HASH_INDEX,
    CREATE_KNOWLEDGE_CREATED_INDEX,
    CREATE_KNOWLEDGE_DELETED_INDEX,
    CREATE_KNOWLEDGE_SOURCE_ACTION_INDEX,
    CREATE_TODOS_CREATED_INDEX,
    CREATE_TODOS_COMPLETED_INDEX,
    CREATE_TODOS_DELETED_INDEX,
    CREATE_DIARIES_DATE_INDEX,
    CREATE_LLM_USAGE_TIMESTAMP_INDEX,
    CREATE_LLM_USAGE_MODEL_INDEX,
    CREATE_LLM_USAGE_MODEL_CONFIG_ID_INDEX,
    CREATE_LLM_MODELS_PROVIDER_INDEX,
    CREATE_LLM_MODELS_IS_ACTIVE_INDEX,
    CREATE_LLM_MODELS_CREATED_AT_INDEX,
    CREATE_EVENTS_START_TIME_INDEX,
    CREATE_EVENTS_CREATED_INDEX,
    CREATE_EVENTS_AGGREGATED_INDEX,
    CREATE_ACTIVITIES_START_TIME_INDEX,
    CREATE_ACTIVITIES_CREATED_INDEX,
    CREATE_ACTIVITIES_UPDATED_INDEX,
    # Three-layer architecture indexes
    CREATE_ACTIONS_TIMESTAMP_INDEX,
    CREATE_ACTIONS_CREATED_INDEX,
    CREATE_ACTIONS_AGGREGATED_INDEX,
    CREATE_ACTIONS_EXTRACT_KNOWLEDGE_INDEX,
    CREATE_ACTION_IMAGES_ACTION_ID_INDEX,
    CREATE_ACTION_IMAGES_HASH_INDEX,
    CREATE_SESSION_PREFERENCES_TYPE_INDEX,
    CREATE_SESSION_PREFERENCES_CONFIDENCE_INDEX,
]
