# API测试指南 - 新架构Insights模块

本文档介绍如何测试新实现的Insights模块API endpoints。

## 🚀 快速开始

### 1. 初始化数据库

首先需要初始化新的数据库schema：

```bash
# 在项目根目录
cd /Users/icyfeather/Projects/Rewind

# 使用Python初始化数据库
python -c "from backend.db.init import init_database; init_database()"
```

### 2. 启动FastAPI服务器

```bash
# 开发模式（自动重载）
uvicorn app:app --reload

# 或使用uv
uv run python app.py
```

### 3. 访问API文档

启动后访问：http://localhost:8000/docs

你将看到所有API endpoints，包括新的insights模块。

---

## 📋 API Endpoints列表

### Events相关

#### 1. 获取最近的Events
- **Endpoint**: `POST /insights/recent-events`
- **描述**: 获取最近N条events记录
- **请求体**:
  ```json
  {
    "limit": 50
  }
  ```
- **响应示例**:
  ```json
  {
    "success": true,
    "data": {
      "events": [
        {
          "id": "uuid-xxx",
          "title": "编写代码",
          "description": "在VSCode中编写Python代码...",
          "keywords": ["编程", "Python"],
          "timestamp": "2025-11-01T10:30:00",
          "created_at": "2025-11-01T10:31:00"
        }
      ],
      "count": 1
    },
    "timestamp": "2025-11-01T10:35:00"
  }
  ```

### Knowledge相关

#### 2. 获取Knowledge列表
- **Endpoint**: `GET /insights/knowledge`
- **描述**: 获取所有knowledge，优先返回combined_knowledge
- **请求体**: 无
- **响应示例**:
  ```json
  {
    "success": true,
    "data": {
      "knowledge": [
        {
          "id": "uuid-xxx",
          "title": "Python异步编程",
          "description": "asyncio库的使用方法...",
          "keywords": ["Python", "async"],
          "created_at": "2025-11-01T10:00:00",
          "type": "combined",
          "merged_from_ids": ["id1", "id2"]
        }
      ],
      "count": 1
    },
    "timestamp": "2025-11-01T10:35:00"
  }
  ```

#### 3. 删除Knowledge
- **Endpoint**: `POST /insights/delete-knowledge`
- **描述**: 软删除指定的knowledge
- **请求体**:
  ```json
  {
    "id": "uuid-xxx"
  }
  ```
- **响应示例**:
  ```json
  {
    "success": true,
    "message": "Knowledge已删除",
    "timestamp": "2025-11-01T10:35:00"
  }
  ```

### Todo相关

#### 4. 获取Todo列表
- **Endpoint**: `POST /insights/todos`
- **描述**: 获取所有todos，优先返回combined_todos
- **请求体**:
  ```json
  {
    "includeCompleted": false
  }
  ```
- **响应示例**:
  ```json
  {
    "success": true,
    "data": {
      "todos": [
        {
          "id": "uuid-xxx",
          "title": "完成项目文档",
          "description": "编写API文档和使用指南",
          "keywords": ["文档", "项目"],
          "created_at": "2025-11-01T09:00:00",
          "completed": false,
          "type": "combined",
          "merged_from_ids": ["id1", "id2"]
        }
      ],
      "count": 1
    },
    "timestamp": "2025-11-01T10:35:00"
  }
  ```

#### 5. 删除Todo
- **Endpoint**: `POST /insights/delete-todo`
- **描述**: 软删除指定的todo
- **请求体**:
  ```json
  {
    "id": "uuid-xxx"
  }
  ```

### Diary相关

#### 6. 生成日记
- **Endpoint**: `POST /insights/generate-diary`
- **描述**: 为指定日期生成日记
- **请求体**:
  ```json
  {
    "date": "2025-11-01"
  }
  ```
- **响应示例**:
  ```json
  {
    "success": true,
    "data": {
      "id": "uuid-xxx",
      "date": "2025-11-01",
      "content": "今天上午我[activity:abc123]完成了项目的核心功能开发[/activity]...",
      "source_activity_ids": ["abc123", "def456"],
      "created_at": "2025-11-01T18:00:00"
    },
    "timestamp": "2025-11-01T18:00:00"
  }
  ```

#### 7. 删除日记
- **Endpoint**: `POST /insights/delete-diary`
- **描述**: 删除指定的日记
- **请求体**:
  ```json
  {
    "id": "uuid-xxx"
  }
  ```

### 统计信息

#### 8. 获取Pipeline统计
- **Endpoint**: `GET /insights/stats`
- **描述**: 获取当前pipeline的运行状态和统计数据
- **请求体**: 无
- **响应示例**:
  ```json
  {
    "success": true,
    "data": {
      "is_running": true,
      "screenshot_threshold": 20,
      "accumulated_screenshots": 5,
      "stats": {
        "total_screenshots": 100,
        "events_created": 5,
        "knowledge_created": 3,
        "todos_created": 2,
        "activities_created": 1,
        "combined_knowledge_created": 1,
        "combined_todos_created": 1,
        "last_processing_time": "2025-11-01T10:30:00"
      }
    },
    "timestamp": "2025-11-01T10:35:00"
  }
  ```

---

## 🧪 使用Postman测试

### 1. 导入集合

创建一个新的Postman Collection，名为"Rewind Insights API"。

### 2. 添加Environment

创建环境变量：
- `base_url`: `http://localhost:8000`

### 3. 测试流程

建议按以下顺序测试：

1. **GET /insights/stats** - 查看pipeline状态
2. **POST /insights/recent-events** - 查看最近的events（需要先有数据）
3. **GET /insights/knowledge** - 查看knowledge列表
4. **GET /insights/todos** - 查看todo列表
5. **POST /insights/generate-diary** - 生成日记
6. **POST /insights/delete-xxx** - 测试删除功能

---

## 🔧 使用curl测试

### 获取Pipeline统计
```bash
curl -X GET "http://localhost:8000/insights/stats"
```

### 获取最近Events
```bash
curl -X POST "http://localhost:8000/insights/recent-events" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

### 获取Knowledge列表
```bash
curl -X GET "http://localhost:8000/insights/knowledge"
```

### 获取Todo列表
```bash
curl -X POST "http://localhost:8000/insights/todos" \
  -H "Content-Type: application/json" \
  -d '{"includeCompleted": false}'
```

### 生成日记
```bash
curl -X POST "http://localhost:8000/insights/generate-diary" \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-01"}'
```

### 删除Knowledge
```bash
curl -X POST "http://localhost:8000/insights/delete-knowledge" \
  -H "Content-Type: application/json" \
  -d '{"id": "your-knowledge-id-here"}'
```

---

## ⚠️ 注意事项

### 1. 数据依赖

- 大部分API需要先有数据才能返回有意义的结果
- Events需要通过pipeline处理raw_records才会产生
- Knowledge/Todo需要通过LLM提取
- Activities需要定时任务聚合events
- Diary依赖于指定日期的activities

### 2. Pipeline启动

新的pipeline需要手动启动：

```python
# 在Python代码中
from backend.processing.pipeline_new import NewProcessingPipeline
import asyncio

pipeline = NewProcessingPipeline()
asyncio.run(pipeline.start())
```

### 3. 配置要求

确保 `backend/config/config.toml` 中有正确的配置：
- LLM API key已配置
- Processing配置已启用
- 语言设置正确（zh或en）

---

## 🐛 故障排查

### 问题1：数据库文件不存在
```
解决方案：运行数据库初始化命令
python -c "from backend.db.init import init_database; init_database()"
```

### 问题2：找不到模块
```
解决方案：确保在项目根目录运行，或添加PYTHONPATH
export PYTHONPATH=/Users/icyfeather/Projects/Rewind:$PYTHONPATH
```

### 问题3：LLM调用失败
```
解决方案：
1. 检查API key配置
2. 检查网络连接
3. 查看日志：logs/backend.log
```

### 问题4：返回空数据
```
解决方案：
1. 确认数据库中有数据
2. 检查pipeline是否已启动
3. 确认raw_records是否已被处理
```

---

## 📝 开发建议

### 1. 本地测试数据

为了快速测试，可以直接在数据库中插入测试数据：

```python
from backend.processing.persistence_new import ProcessingPersistence
import asyncio
import uuid
from datetime import datetime

async def insert_test_data():
    persistence = ProcessingPersistence()

    # 插入测试event
    await persistence.save_event({
        "id": str(uuid.uuid4()),
        "title": "测试事件",
        "description": "这是一个测试事件",
        "keywords": ["测试"],
        "timestamp": datetime.now()
    })

    # 插入测试knowledge
    await persistence.save_knowledge({
        "id": str(uuid.uuid4()),
        "title": "测试知识",
        "description": "这是一个测试知识点",
        "keywords": ["测试", "知识"],
        "created_at": datetime.now()
    })

    print("测试数据已插入")

asyncio.run(insert_test_data())
```

### 2. 查看日志

日志文件位置：`logs/backend.log`

实时查看日志：
```bash
tail -f logs/backend.log
```

---

## ✅ 完整测试检查清单

- [ ] 数据库已初始化
- [ ] FastAPI服务器已启动
- [ ] 访问Swagger UI文档正常
- [ ] GET /insights/stats 返回正常
- [ ] POST /insights/recent-events 返回正常
- [ ] GET /insights/knowledge 返回正常
- [ ] POST /insights/todos 返回正常
- [ ] POST /insights/generate-diary 可生成日记
- [ ] DELETE操作可正常软删除数据
- [ ] PyTauri客户端已重新生成（pnpm tauri dev）

---

祝测试顺利！🎉
