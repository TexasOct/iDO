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

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    error "未找到 uv 命令，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

info "使用 uv 安装依赖..."
PYTAURI_STANDALONE="1" uv pip install \
    --exact \
    --python="$PYTHON_BIN" \
    --reinstall-package=rewind-app \
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

    APP_PATH="$PROJECT_ROOT/src-tauri/target/bundle-release/bundle/macos/Rewind.app"
    MACOS_DIR="$APP_PATH/Contents/MacOS"
    ENTITLEMENTS="$PROJECT_ROOT/src-tauri/entitlements.plist"

    # === 步骤 0: 创建启动包装脚本（解决 DYLD 共享内存限制问题）===
    info "创建启动包装脚本..."

    # 备份原始可执行文件
    if [ ! -f "$MACOS_DIR/rewind-app.bin" ]; then
        mv "$MACOS_DIR/rewind-app" "$MACOS_DIR/rewind-app.bin"
        info "已备份原始可执行文件"
    fi

    # 创建包装脚本
    cat > "$MACOS_DIR/rewind-app" << 'WRAPPER_EOF'
#!/bin/bash
# Rewind 启动包装脚本 - 自动生成，请勿手动编辑

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RESOURCES_DIR="$APP_DIR/Resources"

# 设置 Python 环境变量
export PYTHONHOME="$RESOURCES_DIR"
export PYTHONPATH="$RESOURCES_DIR/lib/python3.14:$RESOURCES_DIR/lib/python3.14/site-packages"

# 设置动态库路径
export DYLD_LIBRARY_PATH="$RESOURCES_DIR/lib:$DYLD_LIBRARY_PATH"
export DYLD_FRAMEWORK_PATH="$RESOURCES_DIR:$DYLD_FRAMEWORK_PATH"

# 关键：禁用 DYLD 共享区域加载，避免内存映射冲突
export DYLD_SHARED_REGION_AVOID_LOADING=1

# 设置工作目录
cd "$APP_DIR"

# 运行真实的可执行文件
exec "$SCRIPT_DIR/rewind-app.bin" "$@"
WRAPPER_EOF

    chmod +x "$MACOS_DIR/rewind-app"
    success "启动包装脚本已创建"
    # === 包装脚本创建完成 ===

    # 步骤 1: 签名所有动态库
    info "正在签名所有动态库文件..."
    DYLIB_COUNT=$(find "$APP_PATH/Contents/Resources" \( -name "*.dylib" -o -name "*.so" \) 2>/dev/null | wc -l | tr -d ' ')

    if [ "$DYLIB_COUNT" -gt 0 ]; then
        info "找到 ${DYLIB_COUNT} 个动态库文件，开始签名..."
        SIGNED_COUNT=$(find "$APP_PATH/Contents/Resources" \( -name "*.dylib" -o -name "*.so" \) \
            -exec codesign --force --deep --sign - {} \; 2>&1 | \
            grep -c "replacing existing signature" || echo "0")
        info "已签名 ${SIGNED_COUNT} 个文件"
        success "动态库签名完成"
    else
        warning "未找到动态库文件"
    fi

    # 步骤 2: 签名可执行文件
    info "签名可执行文件..."
    codesign --force --sign - "$MACOS_DIR/rewind-app.bin" 2>&1 > /dev/null
    codesign --force --sign - "$MACOS_DIR/rewind-app" 2>&1 > /dev/null
    success "可执行文件签名完成"

    # 步骤 3: 使用 entitlements 签名应用包
    if [ -f "$ENTITLEMENTS" ]; then
        info "正在使用 entitlements 签名应用包..."
        codesign --force --deep --sign - \
            --entitlements "$ENTITLEMENTS" \
            "$APP_PATH" 2>&1 && success "应用包签名完成" || warning "应用包签名失败"
    else
        warning "未找到 entitlements.plist，使用默认签名"
        codesign --force --deep --sign - "$APP_PATH" || warning "签名失败"
    fi

    # 步骤 4: 清除扩展属性
    info "清除隔离属性..."
    xattr -cr "$APP_PATH" 2>&1 && success "隔离属性已清除" || warning "清除隔离属性失败"

    # 步骤 5: 验证签名
    info "验证签名状态..."
    if codesign -dvvv "$APP_PATH" 2>&1 | grep -q "Signature=adhoc"; then
        success "签名验证通过 (adhoc 模式)"
    else
        warning "签名验证异常"
    fi

    # 步骤 6: 刷新 Launch Services 数据库
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -v -f "$APP_PATH" 2>&1 > /dev/null || true

    success "macOS 后处理完成 (包括启动包装脚本和代码签名)"
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
elif [ "$OS" = "Linux" ]; then
    echo "  - src-tauri/target/bundle-release/bundle/appimage/"
    echo "  - src-tauri/target/bundle-release/bundle/deb/"
fi

success "✨ 所有步骤完成！"
