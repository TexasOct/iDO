# iDO

> Local-first AI desktop copilot that captures your activity stream, summarizes context with LLMs, and recommends the next task—all on your device.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![Tauri](https://img.shields.io/badge/tauri-2.x-blue.svg)](https://tauri.app/)

---

## 🌟 Why iDO?

- **🔒 Privacy-First**: All data processing happens locally. No cloud uploads required.
- **🏗️ Three-Layer Architecture**: Clean separation (Perception → Processing → Consumption)
- **🤖 AI-Powered**: LLM-driven activity summarization and task recommendations
- **⚡ Modern Stack**: React 19, Python 3.14+, Tauri 2.x, SQLite
- **🔧 Developer-Friendly**: Type-safe, hot reload, auto-generated API clients
- **🌍 Extensible**: Plugin agents, custom LLM providers, modular design

---

## 📐 Architecture at a Glance

```
┌──────────────────────────────────────────────────────────┐
│                  Consumption Layer                       │
│         React UI • Task Recommendations • Agents         │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│                  Processing Layer                        │
│      Event Filtering • LLM Summarization • Database      │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│                  Perception Layer                        │
│       Keyboard • Mouse • Screenshots (20s window)        │
└──────────────────────────────────────────────────────────┘
```

**How it works**:
1. **Perception Layer** captures keyboard, mouse, and screenshots
2. **Processing Layer** filters noise and uses LLM to create meaningful activities
3. **Consumption Layer** displays timeline and generates task recommendations

📖 **[Read the Architecture Guide →](docs/architecture/README.md)**

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Node.js | ≥ 20.x | [nodejs.org](https://nodejs.org/) or `nvm install 20` |
| pnpm | ≥ 9.x | `npm install -g pnpm` |
| Python | ≥ 3.14 | [python.org](https://www.python.org/) or `pyenv install 3.14` |
| uv | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Rust | Latest | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |

### Installation

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

📖 **[Detailed Installation Guide →](docs/getting-started/installation.md)**

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
# Format code (Prettier + Black)
pnpm format

# Lint code (ESLint + Ruff)
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

📖 **[Development Workflow Guide →](docs/getting-started/development-workflow.md)**

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
│   ├── getting-started/   # Installation, first run, workflow
│   ├── architecture/      # System design and data flow
│   ├── guides/            # Frontend, backend, features
│   ├── reference/         # API, database, configuration
│   └── deployment/        # Building and troubleshooting
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
- **Vite 6** - Lightning-fast build tool
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

📖 **[Technology Stack Details →](docs/architecture/tech-stack.md)**

---

## 📖 Documentation

| Section | Description |
|---------|-------------|
| **[Getting Started](docs/getting-started/README.md)** | Installation, first run, development workflow |
| **[Architecture](docs/architecture/README.md)** | System design, data flow, tech stack |
| **[Frontend Guide](docs/guides/frontend/README.md)** | React components, state management, styling |
| **[Backend Guide](docs/guides/backend/README.md)** | API handlers, perception, processing, agents |
| **[Reference](docs/reference/)** | Database schema, API docs, configuration |
| **[Deployment](docs/deployment/)** | Building, signing, troubleshooting |

📚 **[Browse All Documentation →](docs/README.md)**

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

📖 **[Development Workflow Guide →](docs/getting-started/development-workflow.md)**

---

## 🐛 Reporting Issues

Found a bug? Have a feature request?

1. **Search** [existing issues](https://github.com/TexasOct/iDO/issues) first
2. **Create** a new issue with:
   - Clear description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Relevant logs from `~/.config/ido/logs/`

---

## 💬 Community

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/TexasOct/iDO/issues)
- 💡 **Feature Requests**: [GitHub Issues](https://github.com/TexasOct/iDO/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/TexasOct/iDO/discussions)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Tauri](https://tauri.app/) - Modern desktop framework
- Powered by [PyTauri](https://pytauri.github.io/) - Python ↔ Rust bridge
- UI components from [shadcn/ui](https://ui.shadcn.com/)
- Icons from [Lucide](https://lucide.dev/)

---

## 🔗 Links

- **Documentation**: [docs/README.md](docs/README.md)
- **CLAUDE.md**: [CLAUDE.md](CLAUDE.md) - LLM-friendly project guide
- **GitHub**: [github.com/TexasOct/iDO](https://github.com/TexasOct/iDO)

---

<div align="center">

**[📖 Read the Docs](docs/README.md)** • **[🚀 Get Started](docs/getting-started/installation.md)** • **[🤝 Contribute](docs/getting-started/development-workflow.md)**

Made with ❤️ by the iDO team

</div>
