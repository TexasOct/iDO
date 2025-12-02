#!/usr/bin/env bash
set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

info "Cleaning build artifacts..."

# Clean Python environment
if [ -d "src-tauri/pyembed" ]; then
    info "Removing Python environment: src-tauri/pyembed"
    rm -rf src-tauri/pyembed
    success "Python environment removed"
fi

# Clean build targets
if [ -d "src-tauri/target/bundle-release" ]; then
    info "Removing build artifacts: src-tauri/target/bundle-release"
    rm -rf src-tauri/target/bundle-release
    success "Build artifacts removed"
fi

# Clean frontend build
if [ -d "dist" ]; then
    info "Removing frontend build: dist"
    rm -rf dist
    success "Frontend build removed"
fi

success "✨ Cleanup complete!"
echo ""
info "You can now run 'pnpm run bundle' for a complete clean build test"
