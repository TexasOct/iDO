#!/bin/bash

# iDO Project Environment Setup Script for macOS/Linux
# This script initializes the complete project environment including frontend and Python backend

set -e  # Exit on any error

echo "🚀 iDO Project Environment Setup"
echo "===================================="
echo ""

# Color codes for output
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m' # No Color

# Check prerequisites
echo "${BLUE}Checking prerequisites...${NC}"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "${RED}✗ Node.js is not installed${NC}"
    echo "  Please install Node.js v18+ from https://nodejs.org/"
    exit 1
fi
echo "${GREEN}✓ Node.js${NC} $(node --version)"

# Check pnpm
if ! command -v pnpm &> /dev/null; then
    echo "${RED}✗ pnpm is not installed${NC}"
    echo "  Install with: npm install -g pnpm"
    exit 1
fi
echo "${GREEN}✓ pnpm${NC} $(pnpm --version)"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "${RED}✗ Python 3 is not installed${NC}"
    echo "  Please install Python 3.13+ from https://www.python.org/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "${GREEN}✓ Python${NC} $PYTHON_VERSION"

# Check uv
if ! command -v uv &> /dev/null; then
    echo "${RED}✗ uv is not installed${NC}"
    echo "  Install with: pip install uv"
    exit 1
fi
echo "${GREEN}✓ uv${NC} $(uv --version)"

# Check Rust
if ! command -v rustc &> /dev/null; then
    echo "${RED}✗ Rust is not installed${NC}"
    echo "  Please install Rust from https://rustup.rs/"
    exit 1
fi
echo "${GREEN}✓ Rust${NC} $(rustc --version)"

echo ""
echo "${BLUE}Setting up environment...${NC}"
echo ""

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo ""

# Step 1: Install frontend dependencies
echo "${BLUE}[1/3] Installing frontend dependencies...${NC}"
pnpm install
echo "${GREEN}✓ Frontend dependencies installed${NC}"
echo ""

# Step 2: Setup Python backend
echo "${BLUE}[2/3] Setting up Python backend...${NC}"
echo "Running: uv sync"
uv sync
echo "${GREEN}✓ Python backend environment initialized${NC}"
echo ""

# Step 3: Verify i18n translations
echo "${BLUE}[3/3] Verifying i18n translations...${NC}"
pnpm check-i18n
echo "${GREEN}✓ i18n translations verified${NC}"
echo ""

echo "=================================================="
echo "${GREEN}✓ Environment setup completed successfully!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  • Start frontend dev: ${YELLOW}pnpm dev${NC}"
echo "  • Start full Tauri app: ${YELLOW}pnpm tauri dev${NC}"
echo "  • Check frontend: ${YELLOW}pnpm lint${NC}"
echo ""
