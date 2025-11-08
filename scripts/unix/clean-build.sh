#!/usr/bin/env bash
set -euo pipefail

# 颜色输出
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

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

info "清理构建产物..."

# 清理 Python 环境
if [ -d "src-tauri/pyembed" ]; then
    info "删除 Python 环境: src-tauri/pyembed"
    rm -rf src-tauri/pyembed
    success "已删除 Python 环境"
fi

# 清理构建目标
if [ -d "src-tauri/target/bundle-release" ]; then
    info "删除构建产物: src-tauri/target/bundle-release"
    rm -rf src-tauri/target/bundle-release
    success "已删除构建产物"
fi

# 清理前端构建
if [ -d "dist" ]; then
    info "删除前端构建: dist"
    rm -rf dist
    success "已删除前端构建"
fi

success "✨ 清理完成！"
echo ""
info "现在可以运行 'pnpm run bundle' 进行完整的从零开始打包测试"

