# Rewind

Rewind 是一个基于 Tauri 的桌面应用，利用本地采集 + 后端处理 + LLM 总结为用户提供活动感知与智能任务推荐。此 README 仅做高层导引与功能概览；详细的开发、环境与架构说明已拆分到 `docs/` 中的专题文档，便于按需查阅。

---

## 核心价值与功能（高层）
- 实时感知：采集键盘、鼠标、屏幕截图等本地事件（注重隐私与本地优先）。
- 批量处理与摘要：按时间窗口批处理原始记录，利用 LLM 生成事件摘要与活动描述。
- 活动聚合：将相关事件合并为 Activity 并持久化（SQLite）。
- 智能 Agent：基于活动推荐或执行任务（任务可追踪状态：todo → doing → done）。
- 前端呈现：时间轴（Timeline）、活动详情、任务面板，支持主题与多语言（i18n）。

---

## 主要技术栈（简要）
- 前端：React + TypeScript、Vite、Zustand、shadcn/ui + Tailwind
- 后端：PyTauri (Python ↔ Rust)；可选 FastAPI 用于独立后端开发
- 数据存储：SQLite
- 图像/截屏处理：OpenCV / PIL
- 系统监听：pynput / mss
- LLM：OpenAI（可配置）

---

## 快速开始（你应该做的事）
我已把详细安装与开发步骤拆到 `docs/`，请按需打开相应文档开始：

- 入门与环境（必看） — `docs/getting_started.md`
- 架构与设计（概览） — `docs/architecture.md`
- Python 环境与 PyTauri 客户端生成 — `docs/python_environment.md`
- 国际化（i18n）说明 — `docs/internationalization.md`
- 重要文件索引 — `docs/important_files.md`
- 项目特殊说明（自动生成文件、后端约束等） — `docs/special_notes.md`
- 后端 FastAPI 使用（开发/调试） — `docs/fastapi_usage.md`

简要命令（更多细节见 `docs/getting_started.md`）：
- 初始化（项目根）：`pnpm setup`
- 前端开发：`pnpm dev`
- 桌面联合开发（Tauri）：`pnpm tauri dev`
- 后端（FastAPI）开发：`uvicorn app:app --reload`
- 后端变更后同步/生成客户端：`pnpm setup-backend` 或 `uv sync`，随后运行 `pnpm tauri dev` 以触发生成
