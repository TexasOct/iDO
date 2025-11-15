# iDO Documentation

Welcome to the iDO documentation! This guide will help you understand, use, and contribute to iDO.

## 📚 Documentation Structure

### 🚀 [Getting Started](./getting-started/README.md)
New to iDO? Start here!

- [Installation](./getting-started/installation.md) - Set up your development environment
- [First Run](./getting-started/first-run.md) - Configure and test the application
- [Development Workflow](./getting-started/development-workflow.md) - Common development tasks

### 🏗️ [Architecture](./architecture/README.md)
Understand how iDO works

- [Overview](./architecture/README.md) - System architecture overview
- [Three-Layer Design](./architecture/three-layer-design.md) - Perception → Processing → Consumption
- [Data Flow](./architecture/data-flow.md) - How data moves through the system
- [Tech Stack](./architecture/tech-stack.md) - Technology choices and rationale

### 💻 [Development Guides](./guides/)
Learn how to build features

#### Frontend
- [Frontend Overview](./guides/frontend/README.md) - React, TypeScript, Tailwind
- [Components](./guides/frontend/components.md) - Component patterns
- [State Management](./guides/frontend/state-management.md) - Zustand stores
- [Styling](./guides/frontend/styling.md) - Tailwind CSS guidelines

#### Backend  
- [Backend Overview](./guides/backend/README.md) - Python, PyTauri, FastAPI
- [API Handlers](./guides/backend/api-handlers.md) - Unified PyTauri + FastAPI endpoints
- [Perception Layer](./guides/backend/perception-layer.md) - Capture user activity
- [Processing Layer](./guides/backend/processing-layer.md) - Transform events to activities
- [Agents](./guides/backend/agents.md) - AI task recommendation system

#### Features
- [Internationalization](./guides/features/i18n.md) - Multi-language support
- [Permissions](./guides/features/permissions.md) - System permissions (macOS)
- [Screen Capture](./guides/features/screen-capture.md) - Screenshot management
- [Image Optimization](./guides/features/image-optimization.md) - Image processing

### 📖 [Reference](./reference/)
Technical reference documentation

- [Python Environment](./reference/python-environment.md) - Python setup and dependencies
- [Database Schema](./reference/database-schema.md) - SQLite database structure
- [API Reference](./reference/api-reference.md) - Complete API documentation
- [Configuration](./reference/configuration.md) - Config file reference

### 🚀 [Deployment](./deployment/)
Build and distribute iDO

- [Building](./deployment/building.md) - Create production builds
- [macOS Signing](./deployment/macos-signing.md) - Code signing for macOS
- [Troubleshooting](./deployment/troubleshooting.md) - Common issues and solutions

## 🔍 Quick Navigation

### I want to...

**...get started developing iDO**
→ [Installation Guide](./getting-started/installation.md)

**...understand how iDO works**
→ [Architecture Overview](./architecture/README.md)

**...create a new API endpoint**
→ [API Handlers Guide](./guides/backend/api-handlers.md)

**...add a new React component**
→ [Frontend Guide](./guides/frontend/README.md)

**...build an AI agent**
→ [Agents Guide](./guides/backend/agents.md)

**...add a new language**
→ [i18n Guide](./guides/features/i18n.md)

**...modify the database**
→ [Database Schema](./reference/database-schema.md)

**...build for production**
→ [Building Guide](./deployment/building.md)

**...fix a bug**
→ [Troubleshooting](./deployment/troubleshooting.md)

## 📋 Common Tasks

### Development

```bash
# Start development
pnpm setup                  # First-time setup
pnpm dev                    # Frontend only
pnpm tauri:dev:gen-ts      # Full app

# Code quality
pnpm format                 # Format code
pnpm lint                   # Lint code
pnpm tsc                    # Check TypeScript
uv run ty check             # Check Python types
pnpm check-i18n            # Validate translations

# Build
pnpm tauri build           # Production build
pnpm clean                 # Clean artifacts
```

### Adding Features

```bash
# 1. Add backend handler
# Edit backend/handlers/my_feature.py
# Import in backend/handlers/__init__.py
pnpm setup-backend

# 2. Add frontend component
# Edit src/views/MyFeature/index.tsx
# Add route in src/lib/config/menu.ts

# 3. Add translations
# Edit src/locales/en.ts
# Edit src/locales/zh-CN.ts
pnpm check-i18n
```

## 🏛️ Architecture At a Glance

```
┌──────────────────────────────────────────┐
│     Consumption Layer (Frontend)         │
│  React + TypeScript + Tailwind + Zustand │
└─────────────────┬────────────────────────┘
                  │ PyTauri IPC
┌─────────────────▼────────────────────────┐
│     Processing Layer (Backend)           │
│  Python + FastAPI + Pydantic + SQLite    │
└─────────────────┬────────────────────────┘
                  │
┌─────────────────▼────────────────────────┐
│     Perception Layer (Capture)           │
│  pynput + mss + PIL + OpenCV             │
└──────────────────────────────────────────┘
```

## 🎯 Design Principles

1. **Privacy First** - All data processing happens locally
2. **Type Safe** - TypeScript + Pydantic throughout
3. **Developer Friendly** - Hot reload, auto-generation, clear APIs
4. **Extensible** - Plugin agents, modular architecture
5. **Well Documented** - Comprehensive guides and references

## 🤝 Contributing

1. Read the [Development Workflow](./getting-started/development-workflow.md)
2. Follow the [Code Quality](./getting-started/development-workflow.md#code-quality-workflow) guidelines
3. Run tests and type checks before committing
4. Submit a PR with clear description

## 📞 Getting Help

- 🐛 [Report bugs](https://github.com/TexasOct/iDO/issues)
- 💬 [Ask questions](https://github.com/TexasOct/iDO/discussions)
- 📖 [Read CLAUDE.md](../CLAUDE.md) - LLM-friendly project guide

## 📜 License

See [LICENSE](../LICENSE) for details.

---

**Navigation**: [← Back to Project Root](../README.md)
