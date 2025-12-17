![# iDO](assets/iDO_banner.png)

### iDO: Turn every moment into momentum

[English](README.md) | [简体中文](README.zh-CN.md)

> A locally deployed AI desktop assistant that understands your activity stream, uses LLMs to summarize context, helps organize your work and knowledge, and recommends next steps—with all processing done entirely on your device.

[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

---

## 🌟 Why iDO?

- **💻 Cross-Platform**: Support for Windows and macOS
- **🏗️ Three-Layer Architecture**: Clean separation (Perception → Processing → Consumption)
- **🤖 AI-Powered**: LLM-driven activity summarization and task recommendations
- **⚡ Modern Stack**: React 19, Vite 7, Python 3.14+, Tauri 2.x, SQLite
- **🔧 Developer-Friendly**: Type-safe, hot reload, auto-generated API clients
- **🌍 Extensible**: custom LLM providers, modular design

---

## 📐 Architecture at a Glance

<div align="center">
  <img src="assets/arch-en.png" width="50%" alt="architecture"/>
</div>

**How it works**:

1. **Perception Layer** captures keyboard, mouse, and screenshots
2. **Processing Layer** filters noise and uses LLM to create meaningful activities
3. **Consumption Layer** displays timeline and generates task recommendations

📖 **[Read the Architecture Guide →](docs/developers/architecture/README.md)**

---

## 🚀 Quick Start

### For Users

**[Download the latest release →](https://github.com/TexasOct/iDO/releases/latest)**

Follow the installation guide:

- 📖 **[User Installation Guide →](docs/user-guide/installation.md)**
- 🎯 **[Features Overview →](docs/user-guide/features.md)**
- ❓ **[FAQ →](docs/user-guide/faq.md)**

### For Developers

```bash
# Clone the repository
git clone https://github.com/TexasOct/iDO.git
cd iDO

# Windows users: configure git line endings
git config core.autocrlf false

# Install all dependencies (one command!)
pnpm setup
```

This command will:

- ✅ Install frontend dependencies (Node.js)
- ✅ Create Python virtual environment (`.venv`)
- ✅ Install backend dependencies (Python)
- ✅ Validate i18n translations

📖 **[Developer Installation Guide →](docs/developers/getting-started/installation.md)**

---

## 💻 Development

### Start Developing

```bash
# Frontend only (fastest for UI work)
pnpm dev
# → Opens at http://localhost:5173 with hot reload

# Full desktop app (recommended for feature development)
pnpm tauri:dev:gen-ts
# → Launches Tauri app with auto-generated TypeScript client

# Backend API only (for testing endpoints)
uvicorn app:app --reload
# → API docs at http://localhost:8000/docs
```

### Code Quality

```bash
# Format code (Prettier)
pnpm format

# Lint code (Prettier check)
pnpm lint

# Type checking
pnpm tsc              # TypeScript (frontend)
uv run ty check       # Python (backend)

# Validate translations
pnpm check-i18n
```

### Build for Production

```bash
# Standard build
pnpm tauri build

# macOS signed build (requires Apple Developer certificates)
pnpm tauri:build:signed
```

📖 **[Development Workflow Guide →](docs/developers/getting-started/development-workflow.md)**

---

## 📁 Project Structure

```
iDO/
├── src/                    # Frontend (React + TypeScript)
│   ├── views/             # Page components
│   ├── components/        # Reusable UI components
│   ├── lib/
│   │   ├── stores/        # Zustand state management
│   │   ├── client/        # Auto-generated API client (DO NOT EDIT)
│   │   └── types/         # TypeScript types
│   └── locales/           # i18n translations
│
├── backend/               # Backend (Python)
│   ├── handlers/          # API handlers (@api_handler decorator)
│   ├── models/            # Pydantic data models
│   ├── core/              # Core systems (db, events, coordinator)
│   ├── perception/        # Perception layer (capture)
│   ├── processing/        # Processing layer (transform)
│   ├── agents/            # AI agents (recommend)
│   └── config/            # Configuration files
│
├── src-tauri/             # Tauri desktop app
│   ├── python/ido_app/    # PyTauri entry point
│   └── src/               # Rust code
│
├── docs/                  # 📚 Documentation (start here!)
│   ├── user-guide/        # 👥 For end users
│   │   ├── installation.md
│   │   ├── features.md
│   │   ├── faq.md
│   │   └── troubleshooting.md
│   │
│   └── developers/        # 💻 For developers
│       ├── getting-started/   # Setup and workflow
│       ├── architecture/      # System design
│       ├── guides/            # Development guides
│       ├── reference/         # Technical reference
│       └── deployment/        # Building and troubleshooting
│
└── scripts/               # Build and setup scripts
```

---

## 🎯 Key Features

### Privacy-First Design

- ✅ All data processing happens on your device
- ✅ No mandatory cloud uploads
- ✅ User-controlled LLM provider (bring your own API key)
- ✅ Open source and auditable

### Intelligent Activity Tracking

- 📊 Automatic activity detection and grouping
- 🖼️ Smart screenshot deduplication
- 🧠 LLM-powered summarization
- 🔍 Searchable activity timeline

### AI Task Recommendations

- 🤖 Plugin-based agent system
- ✅ Context-aware task suggestions
- 📝 Priority and status tracking
- 🔄 Continuous learning from your patterns

### Developer Experience

- 🔥 Hot reload for frontend and backend
- 📝 Type-safe throughout (TypeScript + Pydantic)
- 🔄 Auto-generated API clients
- 📚 Comprehensive documentation
- 🧪 Easy testing with FastAPI docs

---

## 🛠️ Technology Stack

### Frontend

- **React 19** - UI framework with latest features
- **TypeScript 5** - Type safety
- **Vite 7** - Next-generation build tool (Rolldown)
- **Tailwind CSS 4** - Utility-first styling
- **Zustand 5** - Lightweight state management
- **shadcn/ui** - Accessible component library

### Backend

- **Python 3.14+** - Modern Python with enhanced typing
- **PyTauri 0.8** - Python ↔ Rust bridge
- **FastAPI** - High-performance async web framework
- **Pydantic** - Data validation and serialization
- **SQLite** - Embedded database
- **OpenAI API** - LLM integration (customizable)

### Desktop

- **Tauri 2.x** - Lightweight desktop framework (Rust)
- **Platform APIs** - Native system integration

📖 **[Technology Stack Details →](docs/developers/architecture/tech-stack.md)**

---

## 📖 Documentation

### 👥 For Users

| Guide                                                     | Description                    |
| --------------------------------------------------------- | ------------------------------ |
| **[Installation](docs/user-guide/installation.md)**       | Download and install iDO       |
| **[Features](docs/user-guide/features.md)**               | Learn about iDO's capabilities |
| **[FAQ](docs/user-guide/faq.md)**                         | Frequently asked questions     |
| **[Troubleshooting](docs/user-guide/troubleshooting.md)** | Fix common issues              |

📚 **[Complete User Guide →](docs/user-guide/README.md)**

### 💻 For Developers

| Section                                                          | Description                                  |
| ---------------------------------------------------------------- | -------------------------------------------- |
| **[Getting Started](docs/developers/getting-started/README.md)** | Setup, first run, development workflow       |
| **[Architecture](docs/developers/architecture/README.md)**       | System design, data flow, tech stack         |
| **[Frontend Guide](docs/developers/guides/frontend/README.md)**  | React components, state management, styling  |
| **[Backend Guide](docs/developers/guides/backend/README.md)**    | API handlers, perception, processing, agents |
| **[Reference](docs/developers/reference/)**                      | Database schema, API docs, configuration     |
| **[Deployment](docs/developers/deployment/)**                    | Building, signing, troubleshooting           |

📚 **[Complete Developer Documentation →](docs/developers/README.md)**

---

### 📚 Documentation Hub

**[docs/README.md](docs/README.md)** - Central documentation hub with quick navigation

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Install** dependencies (`pnpm setup`)
4. **Make** your changes
5. **Test** your changes:
   ```bash
   pnpm format        # Format code
   pnpm lint          # Lint code
   pnpm tsc           # Check TypeScript
   uv run ty check    # Check Python types
   pnpm check-i18n    # Validate translations
   ```
6. **Commit** with a clear message (`git commit -m 'Add amazing feature'`)
7. **Push** to your fork (`git push origin feature/amazing-feature`)
8. **Open** a Pull Request

📖 **[Development Workflow Guide →](docs/developers/getting-started/development-workflow.md)**

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Tauri](https://tauri.app/) - Modern desktop framework
- Powered by [PyTauri](https://pytauri.github.io/) - Python ↔ Rust bridge
- UI components from [shadcn/ui](https://ui.shadcn.com/)
- Icons from [Lucide](https://lucide.dev/)

---

<div align="center">

**[📖 Documentation Hub](docs/README.md)** • **[👥 User Guide](docs/user-guide/README.md)** • **[💻 Developer Docs](docs/developers/README.md)** • **[🤝 Contribute](docs/developers/getting-started/development-workflow.md)**

Made with ❤️ by the iDO team

</div>
