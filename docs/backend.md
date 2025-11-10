# 后端架构

本文档详细说明了 iDO 后端系统的架构设计、数据流、以及各个关键组件的实现。

## 目录

- [架构概览](#架构概览)
- [三层架构](#三层架构)
- [数据模型](#数据模型)
- [处理流程](#处理流程)
- [API Handler 系统](#api-handler-系统)
- [Agent 系统](#agent-系统)
- [数据库设计](#数据库设计)
- [最佳实践](#最佳实践)

## 架构概览

iDO 后端采用 **三层分层架构**，数据从底层的原始事件逐层处理和提炼，最终为用户提供智能化的任务建议。

```
┌──────────────────────────────────────────────────────────────────┐
│                    Consumption Layer (消费层)                     │
│                  AI 分析 → 智能推荐 → Agent 执行                  │
│                                                                  │
│  • 活动分析和展示                                                 │
│  • 任务推荐和优先级排序                                           │
│  • Agent 自动执行                                                 │
└──────────────────────────────────────────────────────────────────┘
                                ▲
                                │ 提供高级数据
                                │
┌──────────────────────────────────────────────────────────────────┐
│                    Processing Layer (处理层)                      │
│            事件筛选 → LLM 总结 → 活动合并 → 数据库存储            │
│                                                                  │
│  • 事件过滤和聚合                                                 │
│  • LLM 驱动的文本总结                                             │
│  • 活动合并逻辑                                                   │
│  • 增量更新机制                                                   │
└──────────────────────────────────────────────────────────────────┘
                                ▲
                                │ 提供事件数据
                                │
┌──────────────────────────────────────────────────────────────────┐
│                     Perception Layer (感知层)                     │
│              键盘监控 → 鼠标监控 → 屏幕截图采集                    │
│                                                                  │
│  • 实时事件采集（200ms 周期）                                     │
│  • 20 秒滑动窗口缓冲                                              │
│  • 原始数据存储                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## 三层架构

### 感知层（Perception Layer）

**职责：** 从系统底层采集原始用户活动数据

#### 数据源

1. **键盘事件**（pynput）
   - 按键按下（key press）
   - 按键释放（key release）
   - 组合键检测（Ctrl+C, Shift+A 等）

2. **鼠标事件**（pynput）
   - 点击（click）
   - 滚动（scroll）
   - 拖拽（drag）
   - 移动（move - 可选）

3. **屏幕截图**（mss, PIL, OpenCV）
   - 定期截图采集
   - 图像压缩优化
   - 感知哈希指纹生成

#### 实现细节

```python
# backend/perception/keyboard.py
from pynput import keyboard

def on_press(key):
    raw_record = RawRecord(
        type="keyboard",
        timestamp=datetime.now(),
        data={"key": str(key), "action": "press"}
    )
    # 存储到滑动窗口缓冲

def on_release(key):
    # 类似处理

keyboard.Listener(on_press=on_press, on_release=on_release).start()
```

#### 窗口缓冲机制

- **采集周期：** 200ms
- **缓冲大小：** 20 秒滑动窗口
- **缓冲管理：** 自动过期时间戳超过 20 秒的记录

### 处理层（Processing Layer）

**职责：** 智能处理原始数据，生成有意义的活动概要

#### 处理流程

```
Raw Records (原始记录)
        ↓
   事件筛选 (Event Filtering)
        ↓
   事件聚合 (Event Aggregation)
        ↓
   LLM 总结 (LLM Summarization)
        ↓
   活动合并 (Activity Merging)
        ↓
   数据库存储 (Database Storage)
```

#### 关键特性

1. **事件筛选**
   - 移除无关事件（如鼠标移动）
   - 按事件类型和内容分类
   - 去除重复事件

2. **事件聚合**
   - 将相近时间的事件分组
   - 生成事件摘要（events_summary）
   - 计算统计信息（事件计数、时间跨度等）

3. **LLM 总结**
   - 调用 OpenAI API 对事件进行总结
   - 生成自然语言描述
   - 提取活动关键信息

4. **活动合并**
   - 决定是否合并相邻的事件组
   - 基于时间、内容和意义性判断
   - 形成连贯的活动时间线

5. **增量更新**
   - 版本号控制（version field）
   - 只返回新增数据
   - 防止重复处理

#### 处理周期

- **采集周期：** 每 200ms 采集一次事件
- **处理周期：** 每 10 秒处理一批事件
- **LLM 调用：** 按需调用（可配置频率）

### 消费层（Consumption Layer）

**职责：** 分析活动数据，生成智能推荐和任务

#### 核心功能

1. **活动时间线**
   - 展示历史活动概览
   - 支持时间范围查询
   - 提供详细信息查看

2. **智能分析**
   - 识别用户工作模式
   - 检测异常活动
   - 生成统计仪表板

3. **任务推荐**
   - 基于活动内容推荐任务
   - 支持优先级和分类
   - 跟踪任务执行状态

4. **Agent 系统**
   - 自动化任务执行
   - 可扩展的 Agent 架构
   - 支持并行执行

## 数据模型

### RawRecord（原始记录）

最底层的数据表示，来自系统事件监控。

```python
# backend/models/raw_record.py
class RawRecord(BaseModel):
    """原始系统事件记录"""
    type: str                    # 事件类型：keyboard, mouse, screenshot
    timestamp: datetime         # 事件发生时间
    data: dict                  # 事件数据（类型相关）

    # 示例：
    # {
    #   "type": "keyboard",
    #   "timestamp": "2024-10-29T14:30:00",
    #   "data": {"key": "a", "action": "press"}
    # }
```

### Event（事件）

经过筛选和聚合的事件。

```python
class Event(BaseModel):
    """处理后的事件"""
    id: str
    type: str                   # 事件类型
    timestamp: datetime
    data: dict
    events_summary: str         # 事件摘要（聚合多个原始事件）

    # 示例：
    # {
    #   "type": "keyboard_session",
    #   "timestamp": "2024-10-29T14:30:00",
    #   "data": {...},
    #   "events_summary": "User typed text in editor"
    # }
```

### Activity（活动）

高层的活动表示，代表用户的一段连贯行为。

```python
class Activity(BaseModel):
    """活动记录（持久化到数据库）"""
    id: str
    name: str                   # 活动名称（LLM 生成）
    description: str            # 活动描述
    startTime: datetime
    endTime: datetime
    timestamp: datetime         # 创建时间
    sourceEvents: list[Event]   # 来源事件列表
    version: int                # 版本号（用于增量更新）
    status: str                 # 状态：active, completed

    # 示例：
    # {
    #   "name": "编写代码",
    #   "description": "在 VS Code 中编写 Python 后端代码",
    #   "startTime": "2024-10-29T14:00:00",
    #   "endTime": "2024-10-29T14:45:00",
    #   "sourceEvents": [event1, event2, ...],
    #   "version": 5
    # }
```

### Task（任务）

Agent 系统生成的推荐任务。

```python
class Task(BaseModel):
    """Agent 推荐的任务"""
    id: str
    title: str                  # 任务标题
    description: str            # 任务描述
    relatedActivityId: str      # 相关活动 ID
    status: str                 # 状态：todo, doing, done, cancelled
    priority: str               # 优先级：low, medium, high
    agent_type: str             # 生成此任务的 Agent 类型
    created_at: datetime
    updated_at: datetime
    metadata: dict              # 任务元数据（Agent 相关信息）
```

## 处理流程

### 完整的数据流转

```
[1] 感知层采集
━━━━━━━━━━━━━━━━━━━━
用户操作
  ↓
pynput/mss 采集事件
  ↓
存储到 RawRecord 列表
  ↓
20 秒滑动窗口缓冲

[2] 处理层处理（每 10 秒）
━━━━━━━━━━━━━━━━━━━━
从缓冲读取 RawRecord
  ↓
事件筛选（移除无关事件）
  ↓
事件聚合（分组相近事件）
  ↓
生成 events_summary（事件摘要）
  ↓
调用 LLM 总结（可选，按频率）
  ↓
决定是否合并相邻活动
  ↓
生成 Activity 记录
  ↓
存储到数据库

[3] 消费层分析
━━━━━━━━━━━━━━━━━━━━
前端请求活动列表
  ↓
数据库查询
  ↓
返回 Activity + 统计数据
  ↓
Agent 系统分析
  ↓
生成任务推荐
  ↓
前端展示时间线和建议
```

### 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 采集周期 | 200ms | 每 200ms 采集一次系统事件 |
| 缓冲大小 | 20s | 滑动窗口保留 20 秒内的事件 |
| 处理周期 | 10s | 每 10 秒处理一批缓冲中的事件 |
| 版本更新 | 自增 | 每次 Activity 更新版本号 + 1 |

## API Handler 系统

### 概述

iDO 使用**通用 API Handler 系统**，允许一次定义的 API 接口在 **PyTauri** 和 **FastAPI** 上都自动可用，无需重复代码。

### 核心装饰器

```python
@api_handler(
    body=RequestModel,           # Pydantic 请求模型（可选）
    method="POST",              # HTTP 方法（FastAPI）
    path="/my-endpoint",        # URL 路径（FastAPI）
    tags=["module-name"]        # API 标签（文档）
)
```

### 无参数处理器

```python
# backend/handlers/system.py
@api_handler()
async def get_system_info() -> dict:
    """获取系统信息"""
    return {
        "platform": sys.platform,
        "python_version": sys.version,
        "os": platform.system()
    }

# 使用：
# Python：await get_system_info()
# TypeScript：await apiClient.getSystemInfo()
```

### 有参数处理器

```python
# backend/models/requests.py
class CreateActivityRequest(BaseModel):
    """创建活动请求"""
    name: str
    description: str
    start_time: datetime
    end_time: datetime

# backend/handlers/processing.py
@api_handler(body=CreateActivityRequest, method="POST", path="/activities")
async def create_activity(body: CreateActivityRequest) -> dict:
    """创建新活动"""
    activity = Activity(
        name=body.name,
        description=body.description,
        startTime=body.start_time,
        endTime=body.end_time
    )
    # 保存到数据库
    return {"id": activity.id, "success": True}

# 使用：
# TypeScript：
# await apiClient.createActivity({
#   name: "编写文档",
#   description: "整理项目文档",
#   startTime: new Date(),
#   endTime: new Date()
# })
```

### CamelCase 自动转换

Pydantic 模型自动处理 Python `snake_case` 和 JavaScript `camelCase` 的相互转换。

```python
# Python 模型
class MyRequest(BaseModel):
    field_one: str          # Python: snake_case
    field_two_value: int

# TypeScript 使用
await apiClient.myHandler({
  fieldOne: "value",       // JavaScript: camelCase
  fieldTwoValue: 123
})
```

### 完整示例

```python
# backend/handlers/activity.py
from backend.handlers import api_handler
from backend.models import Activity, CreateActivityRequest

@api_handler(body=CreateActivityRequest, method="POST", path="/activities")
async def create_activity(body: CreateActivityRequest) -> dict:
    """创建新活动"""
    activity = Activity(
        name=body.name,
        description=body.description,
        startTime=body.start_time,
        endTime=body.end_time
    )
    # 保存到数据库
    await db.save(activity)

    return {
        "id": activity.id,
        "name": activity.name,
        "success": True
    }

@api_handler(method="GET", path="/activities/{activity_id}")
async def get_activity(activity_id: str) -> dict:
    """获取活动详情"""
    activity = await db.find_by_id(activity_id)
    return activity.model_dump()
```

详见 [API Handler 系统文档](./api_handler.md)

## Agent 系统

### 架构

Agent 系统是一个**可扩展的智能任务推荐框架**。

```
AgentFactory
    ↓
  ├── BaseAgent (抽象基类)
  │   ├── CodeReviewAgent (代码审查)
  │   ├── DocumentationAgent (文档建议)
  │   ├── HealthCheckAgent (健康检查)
  │   └── ... (自定义 Agent)
```

### 核心概念

#### BaseAgent（基类）

所有 Agent 都继承此基类。

```python
# backend/agents/base.py
class BaseAgent:
    """Agent 基类"""

    async def can_handle(self, activity: Activity) -> bool:
        """判断是否可以处理此活动"""
        raise NotImplementedError

    async def execute(self, activity: Activity) -> Task:
        """执行 Agent 逻辑，生成任务"""
        raise NotImplementedError

    def get_agent_type(self) -> str:
        """返回 Agent 类型标识"""
        raise NotImplementedError
```

#### 具体 Agent 示例

```python
# backend/agents/code_review.py
class CodeReviewAgent(BaseAgent):
    """代码审查 Agent"""

    async def can_handle(self, activity: Activity) -> bool:
        """检查是否涉及代码编写"""
        keywords = ["code", "editor", "programming", "编码", "代码"]
        activity_text = activity.description.lower()
        return any(kw in activity_text for kw in keywords)

    async def execute(self, activity: Activity) -> Task:
        """生成代码审查任务"""
        return Task(
            title="代码审查",
            description=f"请审查在 {activity.start_time} 到 {activity.end_time} 期间编写的代码",
            related_activity_id=activity.id,
            status="todo",
            priority="medium",
            agent_type="code_review"
        )

    def get_agent_type(self) -> str:
        return "code_review"
```

#### AgentFactory（工厂）

```python
# backend/agents/factory.py
class AgentFactory:
    """Agent 工厂"""

    _agents: list[BaseAgent] = []

    @classmethod
    def register(cls, agent: BaseAgent):
        """注册 Agent"""
        cls._agents.append(agent)

    @classmethod
    async def execute(cls, activity: Activity) -> list[Task]:
        """运行所有可用的 Agent，生成任务列表"""
        tasks = []
        for agent in cls._agents:
            if await agent.can_handle(activity):
                task = await agent.execute(activity)
                tasks.append(task)
        return tasks

# 在初始化时注册 Agent
AgentFactory.register(CodeReviewAgent())
AgentFactory.register(DocumentationAgent())
```

### 任务状态流

```
┌─────────┐
│   todo  │  (刚创建的任务)
└────┬────┘
     │ 用户开始
     ↓
┌─────────┐
│  doing  │  (正在进行)
└────┬────┘
     │ 完成或取消
     ↓
┌─────────────┐
│   done  │cancelled  │
└─────────────┘
```

### 添加新 Agent

1. 创建新的 Agent 类继承 `BaseAgent`
2. 实现 `can_handle()` 和 `execute()` 方法
3. 在初始化时注册到 `AgentFactory`

```python
# backend/agents/my_agent.py
class MyAgent(BaseAgent):
    async def can_handle(self, activity: Activity) -> bool:
        # 实现你的逻辑
        pass

    async def execute(self, activity: Activity) -> Task:
        # 生成任务
        pass

    def get_agent_type(self) -> str:
        return "my_agent"

# 在 src-tauri/python/ido_app/__init__.py 中注册
from backend.agents.my_agent import MyAgent
AgentFactory.register(MyAgent())
```

## 数据库设计

### 表结构

#### raw_records 表

```sql
CREATE TABLE raw_records (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,           -- 事件类型
    timestamp DATETIME NOT NULL,   -- 事件时间
    data JSON NOT NULL,           -- 事件数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME           -- 自动过期时间
);

-- 索引
CREATE INDEX idx_raw_records_timestamp ON raw_records(timestamp);
CREATE INDEX idx_raw_records_type ON raw_records(type);
```

#### events 表

```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    data JSON NOT NULL,
    events_summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type ON events(type);
```

#### activities 表

```sql
CREATE TABLE activities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    timestamp DATETIME NOT NULL,
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activities_timestamp ON activities(timestamp);
CREATE INDEX idx_activities_version ON activities(version);
CREATE INDEX idx_activities_date_range ON activities(start_time, end_time);
```

#### activity_events 表（关联表）

```sql
CREATE TABLE activity_events (
    activity_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    PRIMARY KEY (activity_id, event_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id),
    FOREIGN KEY (event_id) REFERENCES events(id)
);
```

#### tasks 表

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    related_activity_id TEXT,
    status TEXT DEFAULT 'todo',  -- todo, doing, done, cancelled
    priority TEXT DEFAULT 'medium',
    agent_type TEXT,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (related_activity_id) REFERENCES activities(id)
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
```

## 最佳实践

### ✅ 代码组织

1. **模块化设计**
   - 每个处理层单独的目录
   - 相关功能放在同一文件
   - 清晰的依赖关系

2. **错误处理**
   ```python
   try:
       result = await process_events()
   except ValueError as e:
       logger.error(f"处理事件失败: {e}")
       return {"error": str(e)}
   ```

3. **日志记录**
   ```python
   logger = logging.getLogger(__name__)
   logger.info(f"处理 {len(events)} 个事件")
   logger.debug(f"事件详情: {event}")
   ```

### ✅ 性能优化

1. **批量处理**
   - 将多个事件合并处理
   - 减少数据库查询次数
   - 按时间窗口分批 LLM 调用

2. **缓存策略**
   - 缓存 LLM 调用结果
   - 使用 Redis（如可用）
   - 减少重复计算

3. **异步编程**
   - 使用 `async/await` 处理 I/O 操作
   - 并行执行多个 Agent
   - 非阻塞的数据库操作

### ✅ 数据一致性

1. **事务管理**
   ```python
   async with db.transaction():
       await db.save(activity)
       await db.update_version(activity.id)
   ```

2. **版本控制**
   - 每次更新递增版本号
   - 防止覆盖更新
   - 支持增量同步

3. **数据验证**
   ```python
   # 使用 Pydantic 自动验证
   activity = Activity(**data)  # 若数据无效会抛出异常
   ```

## 扩展和集成

### 添加新的处理器

参考 `backend/handlers/perception.py` 作为模板

### 添加新的数据源

1. 在感知层添加新的采集器
2. 定义数据模型
3. 集成到处理流程

### 集成外部服务

```python
# 示例：集成第三方分析服务
class ExternalAnalyticsService:
    async def analyze_activity(self, activity: Activity):
        # 调用外部 API
        response = await self.client.post(
            "https://api.external-service.com/analyze",
            json=activity.model_dump()
        )
        return response.json()
```

## 获取帮助

- 📖 查看 [API Handler 文档](./api_handler.md)
- 📖 查看 [开发指南](./development.md)
- 🐛 报告 Bug：[GitHub Issues](https://github.com/TexasOct/iDO/issues)
