# Developer Documentation

Welcome to the iDO developer documentation! This section is for developers who want to compile, develop, or contribute to iDO.

> **Note**: If you just want to use iDO, see the [User Guide](../user-guide/README.md) instead.

## 📚 Documentation Structure

### 🚀 [Getting Started](./getting-started/README.md)
Set up your development environment

- [Installation](./getting-started/installation.md) - Install development tools and dependencies
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

#### Backend
- [Backend Overview](./guides/backend/README.md) - Python, PyTauri, FastAPI

#### Features
- [Internationalization](./guides/features/i18n.md) - Multi-language support

### 📖 [Reference](./reference/)
Technical reference documentation

- Database schema
- API reference
- Configuration files

### 🚀 [Deployment](./deployment/)
Build and distribute iDO

- [Troubleshooting](./deployment/troubleshooting.md) - Common development issues

---

## 🔍 Quick Navigation

### I want to...

**...set up a development environment**
→ [Installation Guide](./getting-started/installation.md)

**...understand how iDO works**
→ [Architecture Overview](./architecture/README.md)

**...create a new API endpoint**
→ [Development Workflow](./getting-started/development-workflow.md)

**...add a new React component**
→ [Frontend Guide](./guides/frontend/README.md)

**...modify the database**
→ [Development Workflow - Database](./getting-started/development-workflow.md#scenario-6-modifying-database-schema)

**...add a new language**
→ [i18n Guide](./guides/features/i18n.md)

**...fix a development issue**
→ [Troubleshooting](./deployment/troubleshooting.md)

---

## 📋 Common Development Commands

### Setup

```bash
# First-time setup
pnpm setup                  # macOS/Linux
pnpm setup:win              # Windows

# Or manual setup
pnpm install                # Frontend dependencies
uv sync                     # Backend dependencies
```

### Development

```bash
# Frontend only (fastest)
pnpm dev

# Full app with TypeScript generation (recommended)
pnpm tauri:dev:gen-ts

# Backend API server only
uvicorn app:app --reload
```

### Code Quality

```bash
# Format and lint
pnpm format                 # Auto-format code
pnpm lint                   # Check code quality

# Type checking
pnpm tsc                    # TypeScript
uv run ty check             # Python

# Validate translations
pnpm check-i18n
```

### Build

```bash
# Production build
pnpm tauri build

# macOS with code signing
pnpm tauri:build:signed

# Clean artifacts
pnpm clean
```

---

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

## 🎯 Development Principles

1. **Privacy First** - All data processing happens locally
2. **Type Safe** - TypeScript + Pydantic throughout
3. **Developer Friendly** - Hot reload, auto-generation, clear APIs
4. **Extensible** - Plugin agents, modular architecture
5. **Well Documented** - Comprehensive guides and references

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Set up** your [development environment](./getting-started/installation.md)
2. **Read** the [development workflow guide](./getting-started/development-workflow.md)
3. **Follow** code quality guidelines (run `pnpm format`, `pnpm lint`, etc.)
4. **Submit** a PR with clear description

See [CLAUDE.md](../../CLAUDE.md) for detailed project rules and best practices.

---

## 📞 Getting Help

- 🐛 [Report bugs](https://github.com/TexasOct/iDO/issues)
- 💬 [Ask questions](https://github.com/TexasOct/iDO/discussions)
- 📖 [Read project rules](../../CLAUDE.md)

---

**Navigation**: [← Back to Documentation Home](../README.md) • [Getting Started →](./getting-started/README.md)
