# Installation Guide

This guide covers everything you need to install and configure iDO for development.

## Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| **Node.js** | ≥ 20.x | Frontend build tooling |
| **pnpm** | ≥ 9.x | Package manager |
| **Python** | ≥ 3.14 | Backend runtime |
| **uv** | Latest | Python package manager |
| **Rust** | Latest stable | Tauri runtime |

### Platform-Specific Requirements

#### macOS
- macOS 13 (Ventura) or later
- Xcode Command Line Tools: `xcode-select --install`
- Accessibility and Screen Recording permissions (granted at first run)

#### Windows
- Windows 10 or later
- Visual Studio Build Tools or Visual Studio with C++ development tools
- PowerShell 5.1 or later

#### Linux
- Ubuntu 20.04+ or equivalent
- Build essentials: `sudo apt install build-essential curl wget`
- X11 or Wayland for GUI

## Step 1: Install Core Tools

### Install Node.js and pnpm

```bash
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20

# Install pnpm globally
npm install -g pnpm
```

### Install Python and uv

```bash
# Install Python 3.14+ (using pyenv recommended)
curl https://pyenv.run | bash
pyenv install 3.14
pyenv global 3.14

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Rust

```bash
# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup default stable
```

## Step 2: Clone the Repository

```bash
git clone https://github.com/TexasOct/iDO.git
cd iDO
```

### Windows-Specific: Configure Git Line Endings

On Windows, you must configure Git to prevent line ending issues:

```bash
git config core.autocrlf false
```

This ensures Git doesn't automatically convert line endings, which can cause issues when collaborating across platforms.

## Step 3: Install Project Dependencies

### Quick Install (Recommended)

```bash
# macOS/Linux
pnpm setup

# Windows
pnpm setup:win
```

This single command will:
- ✅ Install all Node.js dependencies
- ✅ Initialize Python virtual environment (`.venv` in project root)
- ✅ Install Python dependencies
- ✅ Validate i18n translations

### Manual Installation

If you prefer to install dependencies step by step:

```bash
# 1. Install frontend dependencies
pnpm install

# 2. Initialize Python virtual environment
uv sync

# 3. Validate translations
pnpm check-i18n
```

## Step 4: Verify Installation

### Check All Tools

```bash
# Node.js and pnpm
node --version    # Should be ≥ 20.x
pnpm --version    # Should be ≥ 9.x

# Python and uv
python --version  # Should be ≥ 3.14
uv --version

# Rust
rustc --version
cargo --version
```

### Test Frontend Build

```bash
pnpm dev
# Should start dev server at http://localhost:5173
```

### Test Backend

```bash
# Option 1: Standalone FastAPI server
uvicorn app:app --reload
# Visit http://localhost:8000/docs

# Option 2: Full Tauri app
pnpm tauri dev
```

## Troubleshooting

### Python Virtual Environment Issues

**Problem**: `uv sync` fails or Python modules not found

**Solution**:
```bash
# Remove and recreate virtual environment
rm -rf .venv
uv sync

# Verify virtual environment
which python  # Should point to .venv/bin/python
```

### Node Modules Issues

**Problem**: `pnpm install` fails or modules missing

**Solution**:
```bash
# Clean cache and reinstall
pnpm store prune
rm -rf node_modules
pnpm install
```

### Rust Compilation Errors

**Problem**: Tauri fails to compile

**Solution**:
```bash
# Update Rust toolchain
rustup update stable

# Clean build artifacts
pnpm clean

# Rebuild
pnpm tauri build
```

### Windows Line Ending Issues

**Problem**: Git shows many files modified but no actual changes

**Solution**:
```bash
# Configure git
git config core.autocrlf false

# Reset repository
git add .
git reset --hard HEAD
```

### macOS Permission Issues

**Problem**: Application can't monitor keyboard/mouse

**Solution**: See the [Permissions Guide](../guides/features/permissions.md) for detailed instructions on granting macOS accessibility permissions.

## Next Steps

- 🚀 [First Run Guide](./first-run.md) - Configure and test the application
- 💻 [Development Workflow](./development-workflow.md) - Learn common development tasks
- 📖 [Architecture Overview](../architecture/README.md) - Understand the system design

## Additional Resources

- [Python Environment Details](../reference/python-environment.md)
- [Build and Deployment](../deployment/building.md)
- [Troubleshooting Guide](../deployment/troubleshooting.md)
