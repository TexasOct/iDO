# API Handler 系统

本文档详细说明了 iDO 的**通用 API Handler 系统**，该系统允许一次定义的 API 在 PyTauri 和 FastAPI 上自动可用。

## 目录

- [概览](#概览)
- [核心概念](#核心概念)
- [使用指南](#使用指南)
- [常见模式](#常见模式)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

## 概览

### 问题

在传统的 Tauri 应用中，如果想同时支持 PyTauri（桌面）和 FastAPI（Web API），需要定义两套 API：

```python
# ❌ 这样需要重复代码

# PyTauri 命令
@tauri.command
def my_function():
    pass

# 同时需要在 FastAPI 中重复定义
@app.post("/my-function")
async def api_my_function():
    pass
```

### 解决方案

iDO 的 `@api_handler` 装饰器一次定义，自动在两个框架上都可用：

```python
# ✅ 一次定义，两处使用

@api_handler(body=MyRequest, method="POST", path="/my-endpoint")
async def my_handler(body: MyRequest) -> dict:
    return {"success": True}

# 自动注册为：
# - PyTauri 命令：apiClient.myHandler(data)
# - FastAPI 端点：POST /my-endpoint
```

## 核心概念

### 装饰器参数

```python
@api_handler(
    body=RequestModel,                    # Pydantic 请求模型（可选）
    method="POST" | "GET" | "PUT" | ..., # HTTP 方法（FastAPI）
    path="/my-endpoint",                  # URL 路径（FastAPI）
    tags=["module-name"]                  # API 标签和分组
)
```

### 参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `body` | `BaseModel` 子类 | ❌ | Pydantic 请求模型 |
| `method` | str | ❌ | HTTP 方法（默认 GET） |
| `path` | str | ❌ | URL 路径（默认 /command-name） |
| `tags` | list[str] | ❌ | API 标签（用于分组文档） |

### 命名规则

#### PyTauri 命令名称

Python 函数名 → 自动转换为 camelCase：

```python
def my_handler():           # → myHandler
def get_activities():       # → getActivities
def create_user_activity(): # → createUserActivity
```

#### FastAPI 端点

使用显式的 `path` 参数，默认使用函数名：

```python
@api_handler()
async def my_handler():
    # FastAPI 端点：/my-handler
    pass

@api_handler(path="/custom-path")
async def my_handler():
    # FastAPI 端点：/custom-path
    pass
```

## 使用指南

### 无参数处理器

最简单的处理器，不接收任何参数。

```python
# backend/handlers/system.py
from backend.handlers import api_handler

@api_handler()
async def get_system_info() -> dict:
    """获取系统信息"""
    import sys
    import platform

    return {
        "platform": sys.platform,
        "python_version": sys.version,
        "os": platform.system()
    }

# FastAPI 使用
# GET /system-info

# PyTauri 使用
# const info = await apiClient.getSystemInfo()
```

### 有参数的处理器

接收请求体参数的处理器。

```python
# backend/models/requests.py
from backend.models.base import BaseModel

class CreateActivityRequest(BaseModel):
    """创建活动请求"""
    name: str
    description: str
    start_time: datetime
    end_time: datetime

# backend/handlers/processing.py
from backend.handlers import api_handler

@api_handler(
    body=CreateActivityRequest,
    method="POST",
    path="/activities"
)
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
        "success": True
    }

# FastAPI 使用
# POST /activities
# {
#   "name": "编写代码",
#   "description": "在 VS Code 中编写代码",
#   "startTime": "2024-10-29T10:00:00Z",
#   "endTime": "2024-10-29T11:00:00Z"
# }

# PyTauri 使用
# const result = await apiClient.createActivity({
#   name: "编写代码",
#   description: "在 VS Code 中编写代码",
#   startTime: new Date(),
#   endTime: new Date(Date.now() + 3600000)
# })
```

### 路径参数处理

```python
@api_handler(method="GET", path="/activities/{activity_id}")
async def get_activity(activity_id: str) -> dict:
    """获取活动详情"""
    activity = await db.find_by_id(activity_id)
    if not activity:
        return {"error": "Not found"}
    return activity.model_dump()

# FastAPI 使用
# GET /activities/abc123

# PyTauri 使用
# const activity = await apiClient.getActivity("abc123")
```

### 查询参数处理

```python
# FastAPI 自动处理 URL 查询参数
@api_handler(method="GET", path="/activities")
async def list_activities(
    limit: int = 10,
    offset: int = 0,
    status: str | None = None
) -> dict:
    """列出活动（分页）"""
    query = db.query(Activity)

    if status:
        query = query.filter(Activity.status == status)

    activities = await query.limit(limit).offset(offset).all()

    return {
        "data": [a.model_dump() for a in activities],
        "total": await query.count()
    }

# FastAPI 使用
# GET /activities?limit=20&offset=0&status=active

# PyTauri 使用
# const result = await apiClient.listActivities({
#   limit: 20,
#   offset: 0,
#   status: "active"
# })
```

## 常见模式

### 模式 1：CRUD 操作

完整的创建、读取、更新、删除操作。

```python
# backend/models/requests.py
class ActivityRequest(BaseModel):
    name: str
    description: str | None = None

# backend/handlers/activity.py
from backend.handlers import api_handler

# 创建
@api_handler(body=ActivityRequest, method="POST", path="/activities")
async def create_activity(body: ActivityRequest) -> dict:
    activity = Activity(**body.model_dump())
    await db.save(activity)
    return {"id": activity.id, "success": True}

# 读取
@api_handler(method="GET", path="/activities/{activity_id}")
async def get_activity(activity_id: str) -> dict:
    activity = await db.find_by_id(activity_id)
    return activity.model_dump() if activity else {"error": "Not found"}

# 更新
@api_handler(body=ActivityRequest, method="PUT", path="/activities/{activity_id}")
async def update_activity(activity_id: str, body: ActivityRequest) -> dict:
    activity = await db.find_by_id(activity_id)
    if not activity:
        return {"error": "Not found"}

    activity.name = body.name
    activity.description = body.description
    await db.save(activity)
    return {"success": True}

# 删除
@api_handler(method="DELETE", path="/activities/{activity_id}")
async def delete_activity(activity_id: str) -> dict:
    activity = await db.find_by_id(activity_id)
    if not activity:
        return {"error": "Not found"}

    await db.delete(activity)
    return {"success": True}
```

### 模式 2：复杂业务逻辑

包含多步处理的处理器。

```python
class ProcessEventsRequest(BaseModel):
    activity_id: str
    force_llm: bool = False

@api_handler(body=ProcessEventsRequest, method="POST", path="/process")
async def process_activity(body: ProcessEventsRequest) -> dict:
    """处理活动事件"""
    try:
        # 步骤 1：获取活动
        activity = await db.find_by_id(body.activity_id)
        if not activity:
            return {"error": "Activity not found"}

        # 步骤 2：获取相关事件
        events = await db.find_events_for_activity(activity.id)

        # 步骤 3：LLM 分析（如果需要）
        if body.force_llm or not activity.summary:
            summary = await llm_client.summarize(events)
            activity.summary = summary

        # 步骤 4：Agent 分析
        tasks = await agent_factory.execute(activity)

        # 步骤 5：保存结果
        await db.save(activity)

        return {
            "success": True,
            "summary": activity.summary,
            "tasks": [t.model_dump() for t in tasks]
        }

    except Exception as e:
        logger.error(f"Failed to process activity: {e}")
        return {"error": str(e)}
```

### 模式 3：流式响应

处理大数据集的流式返回。

```python
@api_handler(method="GET", path="/activities/export")
async def export_activities() -> dict:
    """导出所有活动"""
    activities = await db.find_all_activities()

    # 分页返回，避免一次性返回太多数据
    items = []
    for activity in activities:
        items.append(activity.model_dump())

        if len(items) >= 100:
            # 返回一批数据
            yield {"data": items}
            items = []

    # 返回剩余数据
    if items:
        yield {"data": items}
```

### 模式 4：异步长时间运行的任务

使用后台任务处理长时间操作。

```python
import asyncio

@api_handler(method="POST", path="/analyze-all")
async def analyze_all_activities() -> dict:
    """分析所有活动（后台任务）"""
    async def background_task():
        activities = await db.find_all_activities()
        for activity in activities:
            await agent_factory.execute(activity)
            await asyncio.sleep(1)  # 避免过载

    # 立即返回，后台继续处理
    asyncio.create_task(background_task())

    return {
        "message": "Analysis started",
        "status": "processing"
    }
```

## CamelCase 自动转换

### 工作原理

所有 Pydantic 模型继承自 `BaseModel`，自动处理 Python snake_case 和 JavaScript camelCase 的转换。

```python
# backend/models/base.py
from pydantic import BaseModel as PydanticModel, ConfigDict

class BaseModel(PydanticModel):
    """基础模型，自动处理 camelCase 转换"""

    model_config = ConfigDict(
        # 允许从 camelCase 接收数据
        alias_generator=to_camel,
        # 在响应中使用 camelCase
        populate_by_name=True,
    )
```

### 示例

```python
# Python 模型（snake_case）
class CreateTaskRequest(BaseModel):
    related_activity_id: str      # Python: snake_case
    assigned_to_user: str
    priority_level: str

# FastAPI 请求（接收 camelCase）
POST /tasks
{
  "relatedActivityId": "abc123",    # JavaScript: camelCase
  "assignedToUser": "john",
  "priorityLevel": "high"
}

# PyTauri 请求（发送 camelCase）
await apiClient.createTask({
  relatedActivityId: "abc123",
  assignedToUser: "john",
  priorityLevel: "high"
})

# FastAPI 响应（返回 camelCase）
{
  "id": "task123",
  "relatedActivityId": "abc123",    # 自动转换为 camelCase
  "createdAt": "2024-10-29T10:00:00Z"
}

# PyTauri 接收（自动转换为 camelCase）
{
  id: "task123",
  relatedActivityId: "abc123",
  createdAt: "2024-10-29T10:00:00Z"
}
```

## TypeScript 客户端生成

### 自动生成过程

当你定义新的处理器后，TypeScript 客户端会**自动生成**。

```
你修改 Python 代码
   ↓
运行 pnpm setup-backend 或 pnpm tauri dev
   ↓
PyTauri 分析 Python 代码和类型
   ↓
自动生成 src/lib/client/ 中的 TypeScript 定义
   ↓
前端代码获得完整的类型提示
```

### 生成的客户端示例

```typescript
// src/lib/client/index.ts (自动生成)
export interface CreateActivityRequest {
  name: string
  description: string
  startTime: Date
  endTime: Date
}

export interface CreateActivityResponse {
  id: string
  success: boolean
}

export async function createActivity(
  body: CreateActivityRequest
): Promise<CreateActivityResponse> {
  // 自动处理 IPC 调用
}
```

### 手动重新生成

如果客户端没有更新，可以手动触发重新生成：

```bash
# 方法 1：清理并重新构建
pnpm tauri build --ci

# 方法 2：运行开发服务器
pnpm tauri dev
```

## 最佳实践

### ✅ 命名约定

1. **函数名称**：使用 `snake_case`，自动转换为 camelCase

   ```python
   def create_user_task():     # → createUserTask
   def get_activity_summary(): # → getActivitySummary
   def update_task_status():   # → updateTaskStatus
   ```

2. **路径**：使用 kebab-case

   ```python
   @api_handler(path="/user-tasks")        # ✅
   @api_handler(path="/user_tasks")        # ❌
   @api_handler(path="/userTasks")         # ❌
   ```

3. **模型字段**：使用 snake_case

   ```python
   class UserTask(BaseModel):
       user_id: str              # ✅ Python: snake_case
       task_status: str
       created_at: datetime
       # 自动转换为 camelCase 在 API 中显示
   ```

### ✅ 错误处理

```python
@api_handler(body=MyRequest)
async def my_handler(body: MyRequest) -> dict:
    try:
        # 处理逻辑
        result = await do_something(body)
        return {"success": True, "data": result}

    except ValueError as e:
        # 返回错误信息（FastAPI 会转换为 HTTP 400）
        return {"success": False, "error": str(e)}

    except Exception as e:
        # 记录错误
        logger.error(f"Unexpected error: {e}")
        # 返回通用错误（FastAPI 会转换为 HTTP 500）
        return {"success": False, "error": "Internal server error"}
```

### ✅ 文档字符串

使用 docstring 为 API 生成文档。

```python
@api_handler(body=CreateTaskRequest, method="POST", path="/tasks")
async def create_task(body: CreateTaskRequest) -> dict:
    """
    创建新任务。

    该端点会创建一个新的任务并将其与相关的活动关联。

    参数：
        body: 任务请求体，包含标题和描述

    返回：
        包含新任务 ID 和成功标志的字典

    异常：
        ValueError: 如果请求数据无效
    """
    # 实现
    pass
```

### ✅ 输入验证

使用 Pydantic 进行自动输入验证。

```python
class TaskRequest(BaseModel):
    """任务请求模型"""
    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    due_date: datetime = Field(...)  # 必需

    @field_validator('title')
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

# Pydantic 自动验证，无效的请求会返回 HTTP 422
```

## 故障排除

### 问题 1：函数参数不被识别

**错误：** "Handler must have either no parameters or a single body parameter"

**原因：** PyTauri 仅支持无参数或单个 `body` 参数

**解决方案：**

```python
# ❌ 错误：多个参数
@api_handler()
async def my_handler(arg1: str, arg2: int):
    pass

# ✅ 正确：无参数
@api_handler()
async def my_handler() -> dict:
    pass

# ✅ 正确：单个 body 参数
@api_handler(body=MyRequest)
async def my_handler(body: MyRequest) -> dict:
    pass
```

### 问题 2：TypeScript 客户端未更新

**症状：** 修改了 Python 代码，但 TypeScript 中没有新函数

**解决方案：**

```bash
# 重新同步后端
pnpm setup-backend

# 或重新生成客户端
pnpm tauri build --ci

# 确保模块已导入
# src-tauri/python/ido_app/__init__.py 中有 from . import my_module
```

### 问题 3：CamelCase 转换不工作

**症状：** 前端发送 `myField`，后端收到的是 `my_field` 为 undefined

**解决方案：**

```python
# 确保模型继承自 BaseModel（包含转换逻辑）
from backend.models.base import BaseModel  # ✅ 正确

class MyRequest(BaseModel):
    my_field: str

# 不要直接继承 Pydantic BaseModel
from pydantic import BaseModel as PydanticModel
# ❌ 这样不会自动转换
```

### 问题 4：API 在 FastAPI 中不显示

**症状：** 访问 http://localhost:8000/docs 没有看到新 API

**解决方案：**

```bash
# 1. 确保函数使用了 @api_handler 装饰器
# 2. 确保模块在 __init__.py 中导入
# 3. 重启 FastAPI 服务器
uvicorn app:app --reload
```

## 获取帮助

- 📖 查看 [后端架构文档](./backend.md)
- 📖 查看 [FastAPI 使用指南](./fastapi_usage.md)
- 📖 查看 [开发指南](./development.md)
- 🐛 报告 Bug：[GitHub Issues](https://github.com/TexasOct/iDO/issues)
