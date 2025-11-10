# Rewind

一个开源的桌面应用，在本地私密地监控并分析你的工作活动，使用 AI 提供智能任务推荐。采用三层架构（Perception → Processing → Consumption），所有处理均在本地进行，保护隐私。

[English](./README.md)

环境：Python 3.14+，TypeScript 5，Tauri 2.x

---

## 核心特性

- 隐私优先：全部本地处理，不上传云端
- 感知层：键盘、鼠标、智能截图（20 秒滑动窗口）
- 处理层：事件筛选、LLM 总结、活动合并、SQLite 持久化
- Agent：基于活动的任务推荐，插件化可扩展
- 现代 UI/UX：React 19、TypeScript 5、Tailwind CSS 4、i18n、明暗主题

---

## 架构

三层设计保证数据流转高效、处理实时：

```
+------------------------------------------+
|   Consumption Layer                      |
|   AI 分析 → 任务推荐 → Agent 执行        |
+------------------------------------------+
              ^
+------------------------------------------+
|   Processing Layer                       |
|   事件筛选 → LLM 总结 → 活动合并 → 持久化 |
+------------------------------------------+
              ^
+------------------------------------------+
|   Perception Layer                       |
|   键盘 → 鼠标 → 屏幕截图                  |
+------------------------------------------+
```

技术栈
- 前端：React 19、TypeScript 5、Vite 6、Tailwind 4
- 桌面：Tauri 2.x（Rust）+ PyTauri 0.8
- 后端：Python 3.14+，开发期使用 FastAPI
- 数据库：SQLite（本地）
- 状态：Zustand 5

---

## 快速开始

环境要求
- macOS / Linux / Windows
- Node.js ≥ 20、Rust（稳定版）、Python ≥ 3.14、uv

初始化
```bash
git clone https://github.com/TexasOct/Rewind.git
cd Rewind

# macOS / Linux
pnpm setup

# Windows
pnpm setup:win

# 或分别安装
pnpm setup-all
```

开发
```bash
# 仅前端
pnpm dev   # http://localhost:5173

# 完整应用（自动生成 TS 客户端，推荐）
pnpm tauri:dev:gen-ts       # macOS/Linux
pnpm tauri:dev:gen-ts:win   # Windows

# 基础 Tauri（不生成 TS）
pnpm tauri dev

# 仅后端（FastAPI）
uvicorn app:app --reload
# 或
uv run python app.py
```

其他命令
```bash
pnpm format        # 代码格式化
pnpm lint          # 格式检查
pnpm check-i18n    # 校验多语言键一致性
pnpm tauri build   # 生产构建
pnpm clean         # 清理产物
```

---

## 目录结构

```
rewind/
├─ src/                      # React 前端
│  ├─ views/                 # 页面
│  ├─ components/            # 复用组件
│  ├─ lib/
│  │  ├─ stores/             # Zustand 状态
│  │  ├─ client/             # 自动生成的 PyTauri 客户端
│  │  ├─ types/              # TS 类型
│  │  └─ config/             # 前端配置（路由/菜单）
│  ├─ hooks/                 # 自定义 hooks（useTauriEvents 等）
│  └─ locales/               # i18n 文件
├─ backend/                  # Python 后端（权威来源）
│  ├─ handlers/              # API（@api_handler）
│  ├─ core/                  # 协调器、DB、事件
│  ├─ models/                # Pydantic 模型
│  ├─ processing/            # 处理流程
│  ├─ perception/            # 键盘、鼠标、截图
│  ├─ agents/                # 任务 Agent
│  └─ llm/                   # LLM 集成
├─ src-tauri/                # Tauri 应用
│  ├─ python/rewind_app/     # PyTauri 入口
│  ├─ src/                   # Rust 代码
│  └─ tauri.conf.json        # 配置
├─ scripts/                  # 开发/构建脚本
└─ docs/                     # 文档
```

---

## 数据流

```
RawRecords（20s 窗口）
  → Events（筛选 + LLM 总结）
  → Activities（聚合）
  → Tasks（Agent 推荐）
  → SQLite（持久化）
```

特点
- 本地处理，无上传
- 增量更新，避免重复
- 截图使用感知哈希去重
- 通过 Tauri 事件实现实时 UI 更新

---

## 文档

- docs/development.md – 环境、初始化、FAQ
- docs/backend.md – 后端架构、模型、Agent
- docs/frontend.md – 组件、状态、数据流
- docs/i18n.md – 多语言配置与校验
- docs/fastapi_usage.md – 使用 FastAPI 开发
- docs/python_environment.md – PyTauri 集成与环境

---

## 常见场景

- 仅前端：`pnpm dev`
- 前后端一起：`pnpm tauri:dev:gen-ts`
- 新增 Python 接口：在 `backend/handlers` 编写并引入到 `backend/handlers/__init__.py`，再运行 `pnpm setup-backend`
- 仅调试后端：`uvicorn app:app --reload`，打开 http://localhost:8000/docs

---

## 通用 API Handler

一次编写，同时适用于 PyTauri 与 FastAPI：

```python
from backend.handlers import api_handler
from backend.models.base import BaseModel

class MyRequest(BaseModel):
    user_input: str

@api_handler(body=MyRequest, method="POST", path="/my-endpoint", tags=["my-module"])
async def my_handler(body: MyRequest) -> dict:
    return {"success": True, "data": body.user_input}
```

前端使用自动生成的类型安全客户端：

```ts
import { apiClient } from '@/lib/client'
await apiClient.myHandler({ userInput: 'value' })
```

---

## 国际化

语言
- zh-CN、en

添加翻译
1) 在 `src/locales/en.ts` 添加键
2) 在 `src/locales/zh-CN.ts` 添加对应键
3) 运行 `pnpm check-i18n`

---

## 隐私与安全

- 本地优先；LLM 使用用户提供的 API Key
- 本地 SQLite；截图自动过期
- 开源透明，可审计

---

## 贡献

- 使用 `pnpm format`、`pnpm lint`、`pnpm check-i18n`
- 倾向严格类型（Pydantic、严格 TS）
- PR 描述清晰；为新功能补充文档

Roadmap（简要）
- 本地 GPU LLM 支持
- 可选云同步
- 浏览器扩展、移动端
- 深度学习活动分类
- 团队协作、更多语言

---

## 致谢

- Tauri、React、shadcn/ui、PyTauri
