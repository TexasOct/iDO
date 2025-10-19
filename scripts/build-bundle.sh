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
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

export PYTAURI_STANDALONE="1"

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    error "未找到 uv 命令，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

info "使用 uv 安装依赖..."
uv pip install \
    --exact \
    --python="$PYTHON_BIN" \
    --reinstall-package=tauri-app \
    . || error "安装依赖失败"

success "依赖安装完成"

# 步骤 3: 配置环境变量
info "步骤 3/4: 配置构建环境..."

export PYO3_PYTHON="$(realpath $PYTHON_BIN)"

# 根据系统配置 RUSTFLAGS
if [ "$OS" = "Linux" ]; then
    if [ -d "$LIBPYTHON_DIR" ]; then
        export RUSTFLAGS="-C link-arg=-Wl,-rpath,\$ORIGIN/../lib/Rewind/lib -L $(realpath $LIBPYTHON_DIR)"
    else
        error "Python 库目录不存在: $LIBPYTHON_DIR"
    fi
elif [ "$OS" = "Darwin" ]; then
    if [ -d "$LIBPYTHON_DIR" ]; then
        export RUSTFLAGS="-C link-arg=-Wl,-rpath,@executable_path/../Resources/lib -L $(realpath $LIBPYTHON_DIR)"
    else
        error "Python 库目录不存在: $LIBPYTHON_DIR"
    fi
fi

info "PYO3_PYTHON: $PYO3_PYTHON"
info "RUSTFLAGS: $RUSTFLAGS"

success "环境配置完成"

# 步骤 4: 执行打包
info "步骤 4/4: 开始打包应用..."

pnpm -- tauri build \
    --config="src-tauri/tauri.bundle.json" \
    -- --profile bundle-release || error "打包失败"

success "打包完成！"

# macOS 特定的后处理
if [ "$OS" = "Darwin" ]; then
    info "执行 macOS 后处理..."
    
    # 清除扩展属性，避免 macOS 隔离问题
    xattr -cr src-tauri/target/bundle-release/bundle/macos/Rewind.app || true
    
    # 刷新 Launch Services 数据库
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -v -f src-tauri/target/bundle-release/bundle/macos/Rewind.app || true
    
    success "后处理完成"
fi

# 显示打包结果位置
info "打包结果位置："
if [ "$OS" = "Darwin" ]; then
    echo "  - src-tauri/target/bundle-release/bundle/macos/Rewind.app"
    echo ""
    info "启动方式："
    echo "  - 推荐：open src-tauri/target/bundle-release/bundle/macos/Rewind.app"
    echo "  - 或者：双击 Rewind.app"
    echo ""
    warning "注意：当前配置只生成 .app 文件，不生成 DMG"
    echo '        如需 DMG 文件，请修改 src-tauri/tauri.bundle.json 中的 targets 为 "all"'
elif [ "$OS" = "Linux" ]; then
    echo "  - src-tauri/target/bundle-release/bundle/appimage/"
    echo "  - src-tauri/target/bundle-release/bundle/deb/"
fi

success "✨ 所有步骤完成！"

