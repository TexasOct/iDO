#!/usr/bin/env bash
set -euo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
PYTHON_VERSION="3.14.0+20251014"


# 打印带颜色的信息
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

info "项目根目录: $PROJECT_ROOT"

# 检测操作系统和架构
OS=$(uname -s)
ARCH=$(uname -m)

info "操作系统: $OS"
info "架构: $ARCH"

# 根据系统确定 Python 下载 URL 和路径
case "$OS" in
    Linux)
        PYTHON_PLATFORM="x86_64-unknown-linux-gnu"
        PYTHON_FILE="cpython-${PYTHON_VERSION}-${PYTHON_PLATFORM}-install_only_stripped.tar.gz"
        PYTHON_URL="https://github.com/astral-sh/python-build-standalone/releases/download/20251014/${PYTHON_FILE}"
        PYTHON_BIN="src-tauri/pyembed/python/bin/python3"
        LIBPYTHON_DIR="src-tauri/pyembed/python/lib"
        ;;
    Darwin)
        if [ "$ARCH" = "arm64" ]; then
            PYTHON_PLATFORM="aarch64-apple-darwin"
        else
            PYTHON_PLATFORM="x86_64-apple-darwin"
        fi
        PYTHON_FILE="cpython-${PYTHON_VERSION}-${PYTHON_PLATFORM}-install_only_stripped.tar.gz"
        PYTHON_URL="https://github.com/astral-sh/python-build-standalone/releases/download/20251014/${PYTHON_FILE}"
        PYTHON_BIN="src-tauri/pyembed/python/bin/python3"
        LIBPYTHON_DIR="src-tauri/pyembed/python/lib"
        ;;
    *)
        error "不支持的操作系统: $OS"
        ;;
esac

# 步骤 1: 下载并解压 portable Python
info "步骤 1/4: 准备 portable Python 环境..."

if [ ! -d "src-tauri/pyembed/python" ]; then
    info "下载 Python: $PYTHON_FILE"

    mkdir -p src-tauri/pyembed
    cd src-tauri/pyembed

    if [ ! -f "$PYTHON_FILE" ]; then
        curl -L -o "$PYTHON_FILE" "$PYTHON_URL" || error "下载 Python 失败"
    fi

    info "解压 Python..."
    tar -xzf "$PYTHON_FILE" || error "解压失败"

    # 清理压缩包
    rm -f "$PYTHON_FILE"

    cd "$PROJECT_ROOT"
    success "Python 环境准备完成"
else
    success "Python 环境已存在，跳过下载"
fi

# 验证 Python 可执行文件
if [ ! -f "$PYTHON_BIN" ]; then
    error "Python 可执行文件不存在: $PYTHON_BIN"
fi

# macOS 特定：修复 libpython 的 install_name
if [ "$OS" = "Darwin" ] && [ -d "$LIBPYTHON_DIR" ]; then
    info "修复 libpython 的 install_name..."
    LIBPYTHON=$(find "$LIBPYTHON_DIR" -name "libpython*.dylib" 2>/dev/null | head -1)
    if [ -f "$LIBPYTHON" ]; then
        LIBPYTHON_NAME=$(basename "$LIBPYTHON")
        install_name_tool -id "@rpath/$LIBPYTHON_NAME" "$LIBPYTHON" || warning "修复 install_name 失败，可能需要手动修复"
        success "已修复 $LIBPYTHON_NAME 的 install_name"
    fi
fi

# 步骤 2: 安装项目依赖到嵌入式 Python 环境
info "步骤 2/4: 安装项目到嵌入式 Python 环境..."

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    error "未找到 uv 命令，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

info "使用 uv 安装依赖..."
PYTAURI_STANDALONE="1" uv pip install \
    --exact \
    --python="$PYTHON_BIN" \
    --reinstall-package=ido-app \
    . || error "安装依赖失败"

success "依赖安装完成"

# 步骤 3: 配置环境变量
info "步骤 3/4: 配置构建环境..."

# 尽量使用 realpath，如果没有则回退到读到的路径
if command -v realpath >/dev/null 2>&1; then
    REAL_PY=$(realpath "$PYTHON_BIN")
else
    REAL_PY="$PYTHON_BIN"
fi
export PYO3_PYTHON="$REAL_PY"

# 根据系统配置 RUSTFLAGS
if [ "$OS" = "Linux" ]; then
    if [ -d "$LIBPYTHON_DIR" ]; then
        if command -v realpath >/dev/null 2>&1; then
            LIBPY_REAL=$(realpath "$LIBPYTHON_DIR")
        else
            LIBPY_REAL="$LIBPYTHON_DIR"
        fi
        export RUSTFLAGS="-C link-arg=-Wl,-rpath,\$ORIGIN/../lib/iDO/lib -L $LIBPY_REAL"
    else
        error "Python 库目录不存在: $LIBPYTHON_DIR"
    fi
elif [ "$OS" = "Darwin" ]; then
    if [ -d "$LIBPYTHON_DIR" ]; then
        if command -v realpath >/dev/null 2>&1; then
            LIBPY_REAL=$(realpath "$LIBPYTHON_DIR")
        else
            LIBPY_REAL="$LIBPYTHON_DIR"
        fi
        export RUSTFLAGS="-C link-arg=-Wl,-rpath,@executable_path/../Resources/lib -L $LIBPY_REAL"
    else
        error "Python 库目录不存在: $LIBPYTHON_DIR"
    fi
fi

info "PYO3_PYTHON: $PYO3_PYTHON"
info "RUSTFLAGS: $RUSTFLAGS"

success "环境配置完成"

# helper: 查找最新生成的 .app（按修改时间）
find_latest_app() {
    local target_dir="src-tauri/target"
    if [ ! -d "$target_dir" ]; then
        return 1
    fi

    # 在 macOS 上使用 stat -f，Linux 使用 stat -c
    if [ "$(uname -s)" = "Darwin" ]; then
        find "$target_dir" -type d -name "*.app" -print0 2>/dev/null | \
            xargs -0 stat -f "%m %N" 2>/dev/null | \
            sort -nr | awk '{$1=""; sub(/^ /,""); print}' | head -n1 || true
    else
        find "$target_dir" -type d -name "*.app" -print0 2>/dev/null | \
            xargs -0 stat -c "%Y %n" 2>/dev/null | \
            sort -nr | awk '{$1=""; sub(/^ /,""); print}' | head -n1 || true
    fi
}

# 步骤 4: 执行打包
info "步骤 4/4: 开始打包应用..."

# On macOS we want to produce both a plain release .app and the bundle (installer) build.
if [ "$OS" = "Darwin" ]; then
    info "macOS: 先构建 release 应用（用于测试/运行），然后构建 bundle（用于发布）"

    # 4.1 Release build (default release profile)
    info "构建 release 应用..."
    pnpm -- tauri build -- --profile release || error "release 打包失败"

    RELEASE_APP=$(find_latest_app || true)
    if [ -n "$RELEASE_APP" ]; then
        success "release 应用已生成: $RELEASE_APP"
    else
        warning "未能定位 release 生成的 .app"
    fi

    # 4.2 Bundle build (使用 bundle config 和 bundle-release profile)
    info "构建 bundle（installer）..."
    pnpm -- tauri build \
        --config="src-tauri/tauri.bundle.json" \
        -- --profile bundle-release || error "bundle 打包失败"

    BUNDLE_APP=$(find_latest_app || true)
    if [ -n "$BUNDLE_APP" ]; then
        # 如果 bundle build 与 release build 都存在，会返回最近修改的那个（通常是 bundle）
        success "bundle 生成的 .app（或打包产物）已生成: $BUNDLE_APP"
    else
        warning "未能定位 bundle 生成的 .app"
    fi
else
    # 非 macOS（Linux 等）按原先行为构建 bundle profile
    pnpm -- tauri build \
        --config="src-tauri/tauri.bundle.json" \
        -- --profile bundle-release || error "打包失败"
    success "打包完成（非 macOS）"
fi

# 显示打包结果位置
info "打包结果位置："
if [ "$OS" = "Darwin" ]; then
    if [ -n "${RELEASE_APP:-}" ]; then
        echo "  - Release app: $RELEASE_APP"
    fi
    if [ -n "${BUNDLE_APP:-}" ]; then
        echo "  - Bundle app: $BUNDLE_APP"
    fi
elif [ "$OS" = "Linux" ]; then
    echo "  - AppImage: src-tauri/target/bundle-release/bundle/appimage/"
    echo "  - DEB: src-tauri/target/bundle-release/bundle/deb/"
fi

success "✨ 构建完成！"
