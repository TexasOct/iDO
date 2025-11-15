# Getting Started with iDO Development

Welcome to iDO development! This guide will help you set up your development environment and start contributing to the project.

> **Note**: If you just want to use iDO without developing, see the [User Guide](../../user-guide/README.md) instead.

## Quick Start

Follow these steps to get iDO running on your machine:

1. **[Installation](./installation.md)** - Install prerequisites and dependencies
2. **[First Run](./first-run.md)** - Configure permissions and test the application
3. **[Development Workflow](./development-workflow.md)** - Learn common development tasks

## What is iDO?

iDO is a local-first AI desktop copilot that:

- 📊 **Captures your activity stream** - Monitors keyboard, mouse, and screenshots
- 🤖 **Summarizes with LLMs** - Uses local AI processing to understand context
- ✅ **Recommends tasks** - Intelligently suggests what to do next
- 🔒 **Privacy-first** - All data stays on your device

## Architecture Overview

iDO uses a **three-layer architecture**:

```
Perception Layer  →  Processing Layer  →  Consumption Layer
  (Capture)           (Analyze)            (Recommend)
```

Learn more in the [Architecture Documentation](../architecture/README.md).

## Tech Stack

- **Frontend**: React 19 + TypeScript 5 + Vite 7 + Tailwind CSS 4
- **Backend**: Python 3.14+ with PyTauri 0.8
- **Desktop**: Tauri 2.x (Rust runtime)
- **Database**: SQLite (local)
- **State Management**: Zustand 5

## Development Commands

```bash
# Install dependencies
pnpm setup

# Frontend only (fast iteration)
pnpm dev

# Full app with backend (recommended)
pnpm tauri:dev:gen-ts

# Backend API server (for testing)
uvicorn app:app --reload

# Code quality checks
pnpm format
pnpm lint
pnpm check-i18n
uv run ty check
pnpm tsc
```

## Next Steps

- 📖 Read the [Installation Guide](./installation.md) to set up your environment
- 🏗️ Explore the [Architecture Documentation](../architecture/README.md)
- 💻 Check out the [Frontend Guide](../guides/frontend/README.md) or [Backend Guide](../guides/backend/README.md)
- 🚀 Learn about [Development Workflows](./development-workflow.md)

## Need Help?

- 📚 Browse the [full documentation](../../README.md)
- 🐛 Report bugs at [GitHub Issues](https://github.com/TexasOct/iDO/issues)
- 💬 Ask questions in [GitHub Discussions](https://github.com/TexasOct/iDO/discussions)

---

**Navigation**: [← Back to Documentation Home](../../README.md) • [Installation →](./installation.md)
