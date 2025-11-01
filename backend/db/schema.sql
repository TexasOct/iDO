-- ============================================================
-- Rewind 数据库Schema（新架构）
-- 用于存储 events, knowledge, todos, activities, diaries
-- ============================================================

-- ============ 基础表 ============

-- Events表（从raw_records提取的事件）
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords TEXT,  -- JSON数组: ["keyword1", "keyword2"]
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge表（原始知识）
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords TEXT,  -- JSON数组
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT 0
);

-- Todos表（原始待办）
CREATE TABLE IF NOT EXISTS todos (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords TEXT,  -- JSON数组
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT 0,
    deleted BOOLEAN DEFAULT 0
);

-- ============ 合并后的表 ============

-- CombinedKnowledge表（合并后的知识）
CREATE TABLE IF NOT EXISTS combined_knowledge (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords TEXT,  -- JSON数组
    merged_from_ids TEXT NOT NULL,  -- JSON数组: ["id1", "id2", ...]
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT 0
);

-- CombinedTodos表（合并后的待办）
CREATE TABLE IF NOT EXISTS combined_todos (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords TEXT,  -- JSON数组
    merged_from_ids TEXT NOT NULL,  -- JSON数组
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT 0,
    deleted BOOLEAN DEFAULT 0
);

-- ============ 活动和日记表 ============

-- Activities表（从events聚合）
CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    source_event_ids TEXT NOT NULL,  -- JSON数组: ["event_id1", "event_id2"]
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT 0
);

-- Diaries表（日记）
CREATE TABLE IF NOT EXISTS diaries (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,  -- YYYY-MM-DD
    content TEXT NOT NULL,
    source_activity_ids TEXT,  -- JSON数组
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT 0
);

-- ============ 索引 ============

-- Events索引
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at DESC);

-- Knowledge索引
CREATE INDEX IF NOT EXISTS idx_knowledge_created ON knowledge(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_deleted ON knowledge(deleted);

-- Todos索引
CREATE INDEX IF NOT EXISTS idx_todos_created ON todos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed);
CREATE INDEX IF NOT EXISTS idx_todos_deleted ON todos(deleted);

-- CombinedKnowledge索引
CREATE INDEX IF NOT EXISTS idx_combined_knowledge_created ON combined_knowledge(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_combined_knowledge_deleted ON combined_knowledge(deleted);

-- CombinedTodos索引
CREATE INDEX IF NOT EXISTS idx_combined_todos_created ON combined_todos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_combined_todos_completed ON combined_todos(completed);
CREATE INDEX IF NOT EXISTS idx_combined_todos_deleted ON combined_todos(deleted);

-- Activities索引
CREATE INDEX IF NOT EXISTS idx_activities_start_time ON activities(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_activities_created ON activities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activities_deleted ON activities(deleted);

-- Diaries索引
CREATE INDEX IF NOT EXISTS idx_diaries_date ON diaries(date DESC);
CREATE INDEX IF NOT EXISTS idx_diaries_deleted ON diaries(deleted);
