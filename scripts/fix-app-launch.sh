#!/bin/bash
# ============================================================================
# Rewind macOS 应用启动修复脚本
# ============================================================================
# 用途: 解决应用通过双击启动时因 DYLD 共享内存限制导致的立即退出问题
# 原理: 创建启动包装脚本，设置正确的环境变量，绕过 DYLD 限制
# 使用: ./scripts/fix-app-launch.sh [app路径]
# ============================================================================

set -e

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

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# 获取应用路径
if [ -n "$1" ]; then
    APP_PATH="$1"
else
    # 默认路径
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    APP_PATH="$PROJECT_ROOT/src-tauri/target/bundle-release/bundle/macos/Rewind.app"
fi

# 检查应用是否存在
if [ ! -d "$APP_PATH" ]; then
    error "应用包不存在: $APP_PATH"
fi

MACOS_DIR="$APP_PATH/Contents/MacOS"
RESOURCES_DIR="$APP_PATH/Contents/Resources"

echo ""
echo "=================================================="
echo "  Rewind macOS 应用启动修复工具"
echo "=================================================="
echo ""
info "应用路径: $APP_PATH"
echo ""

# 步骤 1: 备份原始可执行文件
info "步骤 1/4: 备份原始可执行文件..."

if [ -f "$MACOS_DIR/rewind-app.bin" ]; then
    warning "备份文件已存在，跳过备份"
else
    if [ ! -f "$MACOS_DIR/rewind-app" ]; then
        error "可执行文件不存在: $MACOS_DIR/rewind-app"
    fi

    mv "$MACOS_DIR/rewind-app" "$MACOS_DIR/rewind-app.bin"
    success "已备份: rewind-app → rewind-app.bin"
fi

# 步骤 2: 创建启动包装脚本
info "步骤 2/4: 创建启动包装脚本..."

cat > "$MACOS_DIR/rewind-app" << 'WRAPPER_EOF'
#!/bin/bash
# Rewind 启动包装脚本
# 自动生成，请勿手动编辑

# 获取应用目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RESOURCES_DIR="$APP_DIR/Resources"

# 可选：启用日志记录（用于调试）
# 取消下面两行的注释以启用日志
# LOG_FILE="$HOME/rewind_launch.log"
# exec 1>> "$LOG_FILE" 2>&1

# 可选：调试输出
# echo "=========================================="
# echo "Rewind 启动: $(date)"
# echo "APP_DIR: $APP_DIR"
# echo "RESOURCES_DIR: $RESOURCES_DIR"
# echo "=========================================="

# 设置 Python 环境变量
export PYTHONHOME="$RESOURCES_DIR"
export PYTHONPATH="$RESOURCES_DIR/lib/python3.14:$RESOURCES_DIR/lib/python3.14/site-packages"

# 设置动态库路径
export DYLD_LIBRARY_PATH="$RESOURCES_DIR/lib:$DYLD_LIBRARY_PATH"
export DYLD_FRAMEWORK_PATH="$RESOURCES_DIR:$DYLD_FRAMEWORK_PATH"

# 关键：禁用 DYLD 共享区域加载，避免内存映射冲突
# 这是解决 "DYLD unnest" 警告和应用立即退出问题的核心
export DYLD_SHARED_REGION_AVOID_LOADING=1

# 设置工作目录为应用包根目录
cd "$APP_DIR"

# 运行真实的可执行文件
# 使用 exec 替换当前进程，避免额外的进程层级
exec "$SCRIPT_DIR/rewind-app.bin" "$@"
WRAPPER_EOF

chmod +x "$MACOS_DIR/rewind-app"
success "包装脚本已创建"

# 步骤 3: 重新签名
info "步骤 3/4: 重新签名应用..."

# 签名包装脚本
codesign --force --sign - "$MACOS_DIR/rewind-app" 2>&1 > /dev/null

# 签名原始可执行文件
codesign --force --sign - "$MACOS_DIR/rewind-app.bin" 2>&1 > /dev/null

# 查找 entitlements 文件
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENTITLEMENTS="$PROJECT_ROOT/src-tauri/entitlements.plist"

if [ -f "$ENTITLEMENTS" ]; then
    # 使用 entitlements 签名整个应用
    codesign --force --deep --sign - \
        --entitlements "$ENTITLEMENTS" \
        "$APP_PATH" 2>&1 > /dev/null
    success "已使用 entitlements.plist 签名"
else
    # 使用默认签名
    codesign --force --deep --sign - "$APP_PATH" 2>&1 > /dev/null
    warning "未找到 entitlements.plist，使用默认签名"
fi

# 步骤 4: 移除隔离属性
info "步骤 4/4: 清除隔离属性..."
xattr -cr "$APP_PATH" 2>&1 > /dev/null
success "隔离属性已清除"

# 验证
echo ""
info "验证安装..."
echo "  - 原始可执行文件: $MACOS_DIR/rewind-app.bin"
echo "  - 包装脚本: $MACOS_DIR/rewind-app"
echo "  - 应用包: $APP_PATH"

# 检查签名
if codesign -dvvv "$APP_PATH" 2>&1 | grep -q "Signature=adhoc"; then
    success "签名验证通过 (adhoc 模式)"
else
    warning "签名验证异常"
fi

echo ""
echo "=================================================="
echo "  🎉 修复完成！"
echo "=================================================="
echo ""
echo "现在可以通过以下方式启动应用:"
echo "  1. 双击 Finder 中的 Rewind.app"
echo "  2. 运行: open \"$APP_PATH\""
echo ""
echo "如果需要查看启动日志（用于调试）："
echo "  1. 编辑 $MACOS_DIR/rewind-app"
echo "  2. 取消注释 LOG_FILE 和 exec 重定向行"
echo "  3. 查看日志: tail -f ~/rewind_launch.log"
echo ""
success "所有操作完成！"
