# FastAPI 使用指南

本文档说明了如何使用独立的 FastAPI 服务器进行后端开发和测试，无需运行完整的 Tauri 桌面应用。

## 目录

- [概览](#概览)
- [启动服务器](#启动服务器)
- [API 文档](#api-文档)
- [测试 API](#测试-api)
- [开发工作流](#开发工作流)
- [常见问题](#常见问题)

## 概览

iDO 提供一个**独立的 FastAPI 服务器**，用于快速开发和测试后端功能，无需等待 Tauri 编译。

### 为什么使用 FastAPI？

| 特性 | Tauri 应用 | FastAPI 服务器 |
|------|----------|-------------|
| 启动时间 | 10-30 秒 | < 1 秒 |
| 编译时间 | 30-60 秒 | 无需编译 |
| 热重载 | 有（仅前端） | ✅ 有（全量） |
| 自动文档 | ❌ 无 | ✅ Swagger UI |
| API 测试 | 需要前端 | ✅ 直接测试 |

### 使用场景

- ✅ 新 API 处理器的开发和测试
- ✅ 数据库操作的调试
- ✅ LLM 集成的验证
- ✅ 后端业务逻辑的快速迭代
- ✅ API 文档的查看和学习

## 启动服务器

### 方法 1：使用 uvicorn

```bash
# 进入项目根目录
cd /path/to/iDO

# 启动服务器（开发模式）
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 或指定特定的 IP 和端口
uvicorn app:app --reload --host 127.0.0.1 --port 8080
```

### 方法 2：使用 uv

```bash
# uv 会自动使用项目的 Python 环境
uv run python app.py

# 或手动运行
uv sync && uv run uvicorn app:app --reload
```

### 方法 3：使用 pnpm 脚本

```bash
# 如果项目中配置了脚本
pnpm backend:dev
```

### 启动输出

成功启动后会看到：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 选项说明

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--reload` | 代码变化时自动重启 | disabled |
| `--host` | 监听的 IP 地址 | `127.0.0.1` |
| `--port` | 监听的端口 | `8000` |
| `--workers` | 工作进程数量 | `1` |

## API 文档

### Swagger UI

```
http://localhost:8000/docs
```

**特点：**
- ✅ 所有 API 端点的完整列表
- ✅ 请求/响应示例
- ✅ 在线 API 测试
- ✅ 参数和返回类型文档

### ReDoc

```
http://localhost:8000/redoc
```

**特点：**
- ✅ 更详细的文档
- ✅ 搜索功能
- ✅ 离线可用

### OpenAPI 文档

```
http://localhost:8000/openapi.json
```

机器可读的 OpenAPI 规范

## 测试 API

### 在 Swagger UI 中测试

1. 打开 http://localhost:8000/docs
2. 找到你要测试的 API 端点
3. 点击端点展开详情
4. 点击 "Try it out" 按钮
5. 填入参数和请求体
6. 点击 "Execute" 发送请求

### 使用 curl 测试

#### GET 请求

```bash
# 获取系统信息
curl http://localhost:8000/system/info

# 获取活动列表
curl http://localhost:8000/activities
```

#### POST 请求

```bash
# 创建活动
curl -X POST http://localhost:8000/activities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "编写代码",
    "description": "在 VS Code 中编写 Python 代码",
    "startTime": "2024-10-29T10:00:00",
    "endTime": "2024-10-29T11:00:00"
  }'
```

#### 带认证的请求

```bash
# 如果 API 需要 API Key
curl http://localhost:8000/activities \
  -H "Authorization: Bearer your-api-key"
```

### 使用 Python 测试

```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        # GET 请求
        response = await client.get('http://localhost:8000/system/info')
        print(response.json())

        # POST 请求
        response = await client.post(
            'http://localhost:8000/activities',
            json={
                'name': '编写代码',
                'description': '在 VS Code 中编写代码',
                'startTime': '2024-10-29T10:00:00',
                'endTime': '2024-10-29T11:00:00'
            }
        )
        print(response.json())

asyncio.run(test_api())
```

### 使用 JavaScript/TypeScript 测试

```typescript
// 使用 fetch API
const response = await fetch('http://localhost:8000/activities', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: '编写代码',
    description: '在 VS Code 中编写代码',
    startTime: new Date().toISOString(),
    endTime: new Date(Date.now() + 3600000).toISOString(),
  }),
})

const data = await response.json()
console.log(data)

// 使用 axios
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

const response = await api.post('/activities', {
  name: '编写代码',
  // ...
})
```

### 使用 Postman 测试

1. 打开 Postman
2. 导入 OpenAPI 文档：
   ```
   http://localhost:8000/openapi.json
   ```
3. Postman 会自动生成所有 API 端点
4. 选择端点，填入参数，点击 Send

## 开发工作流

### 场景 1：开发新的 API 处理器

```bash
# 1. 启动 FastAPI 开发服务器
uvicorn app:app --reload

# 2. 编辑 backend/handlers/my_handler.py
# 示例：
# @api_handler(body=MyRequest, method="POST", path="/my-endpoint")
# async def my_handler(body: MyRequest) -> dict:
#     return {"success": True, "data": body.field}

# 3. 服务器自动重启，访问文档
# http://localhost:8000/docs

# 4. 在 Swagger UI 中测试新 API

# 5. 所有改动自动保存
```

### 场景 2：修改数据模型

```bash
# 1. 编辑 backend/models/requests.py
# 2. 服务器自动重启
# 3. 访问 http://localhost:8000/docs 查看更新后的 API 文档
```

### 场景 3：调试 LLM 集成

```python
# backend/handlers/processing.py
import logging

logger = logging.getLogger(__name__)

@api_handler(body=ProcessRequest)
async def process_activity(body: ProcessRequest) -> dict:
    logger.debug(f"Processing activity: {body.name}")

    # 调用 LLM
    response = await llm_client.summarize(body.events)
    logger.debug(f"LLM response: {response}")

    return {"summary": response}
```

然后在服务器日志中查看调试信息。

### 场景 4：测试异常处理

```python
@api_handler()
async def test_error() -> dict:
    raise ValueError("这是一个测试错误")

# 访问 http://localhost:8000/docs
# 测试端点后会返回 HTTP 500 和错误详情
```

## 常见问题

### Q1：启动时提示"端口被占用"

**错误信息：**
```
OSError: [Errno 48] Address already in use
```

**解决方案：**

```bash
# 使用不同的端口
uvicorn app:app --port 8001

# 或找出占用端口的进程并杀死
lsof -i :8000
kill -9 <PID>
```

### Q2：Python 模块导入错误

**错误信息：**
```
ModuleNotFoundError: No module named 'backend'
```

**解决方案：**

```bash
# 1. 确保在项目根目录运行
cd /path/to/iDO

# 2. 重新同步 Python 环境
uv sync

# 3. 重启服务器
uvicorn app:app --reload
```

### Q3：如何看到详细的日志？

```bash
# 增加日志级别
uvicorn app:app --reload --log-level debug
```

### Q4：如何修改 API 响应的默认 Host？

Swagger UI 默认使用 http://localhost:8000。如果需要改变：

```bash
# 启动时指定 host
uvicorn app:app --host 0.0.0.0 --port 8000

# 然后访问 http://your-ip:8000/docs
```

### Q5：FastAPI 和 Tauri 版本的 API 是否完全相同？

是的，它们使用相同的 `@api_handler` 装饰器，生成的 API 完全相同。

**唯一的区别：**
- **Tauri 版本**：通过 PyTauri 调用，通过 IPC 通信
- **FastAPI 版本**：通过 HTTP REST API 调用

## 高级用法

### 启用 CORS

如果前端在不同的端口运行，需要启用 CORS：

```python
# app.py
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 添加中间件进行日志记录

```python
import time

@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    print(f"{request.method} {request.url.path} - {duration:.2f}s")
    return response
```

### 生产环境部署

```bash
# 使用 Gunicorn (多工作进程)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app

# 或使用 uvicorn 的多工作进程
uvicorn app:app --workers 4 --host 0.0.0.0 --port 8000
```

## 与 Tauri 桌面应用的集成

### 使用 FastAPI 进行开发

1. 启动 FastAPI 服务器：`uvicorn app:app --reload`
2. 使用 Swagger UI 进行 API 开发和测试
3. 一旦后端稳定，启动完整的 Tauri 应用

### 前端连接到本地 FastAPI

如果需要前端连接到本地 FastAPI 而不是 Tauri 桌面应用：

```typescript
// 配置 API 客户端使用 HTTP
import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function fetchActivities() {
  const response = await apiClient.get('/activities')
  return response.data
}
```

## 获取帮助

- 📖 查看 [后端架构文档](./backend.md)
- 📖 查看 [API Handler 文档](./api_handler.md)
- 📖 查看 [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- 🐛 报告 Bug：[GitHub Issues](https://github.com/TexasOct/iDO/issues)
