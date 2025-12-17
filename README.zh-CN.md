![# iDO](assets/iDO_banner.png)

### iDO: Turn every moment into momentum

[English](README.md) | [简体中文](README.zh-CN.md)

> 本地部署的 AI 桌面助手，读懂你的活动流，使用 LLM 总结上下文，帮你整理所做的事情、所学的知识并推荐下一步任务——所有处理都在你的设备上完成。

[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

---

## 🌟 为什么选择 iDO？

- **💻 跨平台支持**：支持 Windows 和 macOS
- **🏗️ 三层架构**：清晰的分层设计（感知层 → 处理层 → 消费层）
- **🤖 AI 驱动**：基于 LLM 的活动总结和任务推荐
- **⚡ 现代技术栈**：React 19、Vite 7、Python 3.14+、Tauri 2.x、SQLite
- **🔧 开发者友好**：类型安全、热重载、自动生成 API 客户端
- **🌍 可扩展**：自定义 LLM 提供商、模块化设计

---

## 📐 架构概览

<div align="center">
  <img src="assets/arch-zh.png" width="50%" alt="architecture"/>
</div>

**工作原理**：

1. **感知层** 捕获键盘、鼠标和屏幕截图
2. **处理层** 过滤噪音，使用 LLM 创建有意义的活动记录
3. **消费层** 显示时间线并生成任务推荐

📖 **[阅读架构指南 →](docs/developers/architecture/README.md)**

---

## 🚀 快速开始

### 普通用户

**[下载最新版本 →](https://github.com/TexasOct/iDO/releases/latest)**

按照安装指南操作：

- 📖 **[用户安装指南 →](docs/user-guide/installation.md)**
- 🎯 **[功能概览 →](docs/user-guide/features.md)**
- ❓ **[常见问题 →](docs/user-guide/faq.md)**

### 开发者

```bash
# 克隆仓库
git clone https://github.com/TexasOct/iDO.git
cd iDO

# Windows 用户：配置 git 换行符
git config core.autocrlf false

# 安装所有依赖（一条命令搞定！）
pnpm setup
```

这条命令会：

- ✅ 安装前端依赖（Node.js）
- ✅ 创建 Python 虚拟环境（`.venv`）
- ✅ 安装后端依赖（Python）
- ✅ 验证 i18n 翻译

📖 **[开发者安装指南 →](docs/developers/getting-started/installation.md)**

---

## 💻 开发

### 开始开发

```bash
# 仅前端（UI 开发最快）
pnpm dev
# → 在 http://localhost:5173 打开，支持热重载

# 完整桌面应用（推荐用于功能开发）
pnpm tauri:dev:gen-ts
# → 启动 Tauri 应用，自动生成 TypeScript 客户端

# 仅后端 API（用于测试端点）
uvicorn app:app --reload
# → API 文档位于 http://localhost:8000/docs
```

### 代码质量

```bash
# 格式化代码（Prettier）
pnpm format

# 检查代码（Prettier check）
pnpm lint

# 类型检查
pnpm tsc              # TypeScript（前端）
uv run ty check       # Python（后端）

# 验证翻译
pnpm check-i18n
```

### 生产构建

```bash
# 标准构建
pnpm tauri build

# macOS 签名构建（需要 Apple 开发者证书）
pnpm tauri:build:signed
```

📖 **[开发工作流指南 →](docs/developers/getting-started/development-workflow.md)**

---

## 📁 项目结构

```
iDO/
├── src/                    # 前端（React + TypeScript）
│   ├── views/             # 页面组件
│   ├── components/        # 可复用 UI 组件
│   ├── lib/
│   │   ├── stores/        # Zustand 状态管理
│   │   ├── client/        # 自动生成的 API 客户端（勿手动编辑）
│   │   └── types/         # TypeScript 类型
│   └── locales/           # i18n 翻译
│
├── backend/               # 后端（Python）
│   ├── handlers/          # API 处理器（@api_handler 装饰器）
│   ├── models/            # Pydantic 数据模型
│   ├── core/              # 核心系统（db、events、coordinator）
│   ├── perception/        # 感知层（捕获）
│   ├── processing/        # 处理层（转换）
│   ├── agents/            # AI agents（推荐）
│   └── config/            # 配置文件
│
├── src-tauri/             # Tauri 桌面应用
│   ├── python/ido_app/    # PyTauri 入口
│   └── src/               # Rust 代码
│
├── docs/                  # 📚 文档（从这里开始！）
│   ├── user-guide/        # 👥 普通用户
│   │   ├── installation.md
│   │   ├── features.md
│   │   ├── faq.md
│   │   └── troubleshooting.md
│   │
│   └── developers/        # 💻 开发者
│       ├── getting-started/   # 设置和工作流
│       ├── architecture/      # 系统设计
│       ├── guides/            # 开发指南
│       ├── reference/         # 技术参考
│       └── deployment/        # 构建和故障排除
│
└── scripts/               # 构建和设置脚本
```

---

## 🎯 核心功能

### 隐私优先设计

- ✅ 所有数据处理都在你的设备上进行
- ✅ 无强制云上传
- ✅ 用户控制 LLM 提供商（使用自己的 API 密钥）
- ✅ 开源且可审计

### 智能活动跟踪

- 📊 自动活动检测和分组
- 🖼️ 智能截图去重
- 🧠 LLM 驱动的总结
- 🔍 可搜索的活动时间线

### AI 任务推荐

- 🤖 基于插件的 Agent 系统
- ✅ 上下文感知的任务建议
- 📝 优先级和状态跟踪
- 🔄 从你的使用模式中持续学习

### 开发者体验

- 🔥 前端和后端热重载
- 📝 全栈类型安全（TypeScript + Pydantic）
- 🔄 自动生成 API 客户端
- 📚 完善的文档
- 🧪 使用 FastAPI 文档轻松测试

---

## 🛠️ 技术栈

### 前端

- **React 19** - UI 框架，使用最新特性
- **TypeScript 5** - 类型安全
- **Vite 7** - 下一代构建工具（Rolldown）
- **Tailwind CSS 4** - 实用优先的样式
- **Zustand 5** - 轻量级状态管理
- **shadcn/ui** - 无障碍组件库

### 后端

- **Python 3.14+** - 现代 Python，增强类型系统
- **PyTauri 0.8** - Python ↔ Rust 桥接
- **FastAPI** - 高性能异步 Web 框架
- **Pydantic** - 数据验证和序列化
- **SQLite** - 嵌入式数据库
- **OpenAI API** - LLM 集成（可自定义）

### 桌面

- **Tauri 2.x** - 轻量级桌面框架（Rust）
- **平台 API** - 原生系统集成

📖 **[技术栈详情 →](docs/developers/architecture/tech-stack.md)**

---

## 📖 文档

### 👥 普通用户

| 指南                                               | 描述            |
| -------------------------------------------------- | --------------- |
| **[安装](docs/user-guide/installation.md)**        | 下载和安装 iDO  |
| **[功能](docs/user-guide/features.md)**            | 了解 iDO 的功能 |
| **[常见问题](docs/user-guide/faq.md)**             | 常见问题解答    |
| **[故障排除](docs/user-guide/troubleshooting.md)** | 解决常见问题    |

📚 **[完整用户指南 →](docs/user-guide/README.md)**

### 💻 开发者

| 章节                                                      | 描述                           |
| --------------------------------------------------------- | ------------------------------ |
| **[入门指南](docs/developers/getting-started/README.md)** | 设置、首次运行、开发工作流     |
| **[架构](docs/developers/architecture/README.md)**        | 系统设计、数据流、技术栈       |
| **[前端指南](docs/developers/guides/frontend/README.md)** | React 组件、状态管理、样式     |
| **[后端指南](docs/developers/guides/backend/README.md)**  | API 处理器、感知、处理、agents |
| **[参考](docs/developers/reference/)**                    | 数据库模式、API 文档、配置     |
| **[部署](docs/developers/deployment/)**                   | 构建、签名、故障排除           |

📚 **[完整开发者文档 →](docs/developers/README.md)**

---

### 📚 文档中心

**[docs/README.md](docs/README.md)** - 中央文档中心，快速导航

---

## 🤝 贡献

我们欢迎贡献！以下是入门步骤：

1. **Fork** 仓库
2. **创建** 功能分支（`git checkout -b feature/amazing-feature`）
3. **安装** 依赖（`pnpm setup`）
4. **进行** 修改
5. **测试** 你的修改：
   ```bash
   pnpm format        # 格式化代码
   pnpm lint          # 检查代码
   pnpm tsc           # 检查 TypeScript
   uv run ty check    # 检查 Python 类型
   pnpm check-i18n    # 验证翻译
   ```
6. **提交** 并附上清晰的消息（`git commit -m 'Add amazing feature'`）
7. **推送** 到你的 fork（`git push origin feature/amazing-feature`）
8. **打开** Pull Request

📖 **[开发工作流指南 →](docs/developers/getting-started/development-workflow.md)**

---

## 📄 许可证

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 基于 [Tauri](https://tauri.app/) 构建 - 现代桌面框架
- 由 [PyTauri](https://pytauri.github.io/) 驱动 - Python ↔ Rust 桥接
- UI 组件来自 [shadcn/ui](https://ui.shadcn.com/)
- 图标来自 [Lucide](https://lucide.dev/)

---

<div align="center">

**[📖 文档中心](docs/README.md)** • **[👥 用户指南](docs/user-guide/README.md)** • **[💻 开发者文档](docs/developers/README.md)** • **[🤝 贡献](docs/developers/getting-started/development-workflow.md)**

iDO 团队用 ❤️ 制作

</div>
