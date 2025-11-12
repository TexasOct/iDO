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
        start_time TEXT,
        end_time TEXT,
        type TEXT,
        summary TEXT,
        source_data TEXT,
        title TEXT DEFAULT '',
        description TEXT DEFAULT '',
        keywords TEXT,
        timestamp TEXT,
        deleted BOOLEAN DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_ACTIVITIES_TABLE = """
    CREATE TABLE IF NOT EXISTS activities (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        source_events TEXT,
        source_event_ids TEXT,
        version INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted BOOLEAN DEFAULT 0
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
        metadata TEXT
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
        prompt_tokens INTEGER NOT NULL DEFAULT 0,
        completion_tokens INTEGER NOT NULL DEFAULT 0,
        total_tokens INTEGER NOT NULL DEFAULT 0,
        cost REAL DEFAULT 0.0,
        request_type TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
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

CREATE_EVENTS_TIMESTAMP_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_events_timestamp
    ON events(timestamp DESC)
"""

CREATE_EVENTS_CREATED_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_events_created
    ON events(created_at DESC)
"""

# All table creation statements in order
ALL_TABLES = [
    CREATE_RAW_RECORDS_TABLE,
    CREATE_EVENTS_TABLE,
    CREATE_ACTIVITIES_TABLE,
    CREATE_TASKS_TABLE,
    CREATE_SETTINGS_TABLE,
    CREATE_CONVERSATIONS_TABLE,
    CREATE_MESSAGES_TABLE,
    CREATE_LLM_TOKEN_USAGE_TABLE,
    CREATE_EVENT_IMAGES_TABLE,
    CREATE_LLM_MODELS_TABLE,
]

# All index creation statements
ALL_INDEXES = [
    CREATE_MESSAGES_CONVERSATION_INDEX,
    CREATE_CONVERSATIONS_UPDATED_INDEX,
    CREATE_EVENT_IMAGES_EVENT_ID_INDEX,
    CREATE_EVENT_IMAGES_HASH_INDEX,
    CREATE_LLM_USAGE_TIMESTAMP_INDEX,
    CREATE_LLM_USAGE_MODEL_INDEX,
    CREATE_LLM_MODELS_PROVIDER_INDEX,
    CREATE_LLM_MODELS_IS_ACTIVE_INDEX,
    CREATE_LLM_MODELS_CREATED_AT_INDEX,
    CREATE_EVENTS_TIMESTAMP_INDEX,
    CREATE_EVENTS_CREATED_INDEX,
]
