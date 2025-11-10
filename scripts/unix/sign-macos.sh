#!/bin/bash

# macOS 应用签名修复脚本
# 用途: 解决 adhoc 签名导致的双击无法启动问题
# 使用: sh scripts/sign-macos.sh

set -e  # 遇到错误立即退出

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 应用路径
APP_PATH="$PROJECT_ROOT/src-tauri/target/bundle-release/bundle/macos/iDO.app"
ENTITLEMENTS="$PROJECT_ROOT/src-tauri/entitlements.plist"

printf "${BLUE}================================================${NC}\n"
printf "${BLUE}  iDO macOS 应用签名修复工具${NC}\n"
printf "${BLUE}================================================${NC}\n"
printf "\n"

# 检查应用是否存在
if [ ! -d "$APP_PATH" ]; then
    printf "${RED}❌ 错误: 未找到应用包${NC}\n"
    printf "${YELLOW}路径: $APP_PATH${NC}\n"
    printf "${YELLOW}请先运行: pnpm tauri build${NC}\n"
    exit 1
fi

printf "${GREEN}✓${NC} 找到应用包: ${APP_PATH##*/}\n"
printf "\n"

# 检查 entitlements 文件
if [ ! -f "$ENTITLEMENTS" ]; then
    printf "${RED}❌ 错误: 未找到 entitlements.plist${NC}\n"
    printf "${YELLOW}路径: $ENTITLEMENTS${NC}\n"
    exit 1
fi

printf "${GREEN}✓${NC} 找到 entitlements 文件\n"
printf "\n"

# 步骤 1: 签名所有动态库
printf "${BLUE}[1/3]${NC} 正在签名所有动态库文件...\n"
printf "${YELLOW}      这可能需要 10-30 秒...${NC}\n"

DYLIB_COUNT=$(find "$APP_PATH/Contents/Resources" \( -name "*.dylib" -o -name "*.so" \) | wc -l | tr -d ' ')
printf "${YELLOW}      找到 ${DYLIB_COUNT} 个动态库文件${NC}\n"

find "$APP_PATH/Contents/Resources" \( -name "*.dylib" -o -name "*.so" \) \
    -exec codesign --force --deep --sign - {} \; 2>&1 | \
    grep -E "replacing existing signature" | wc -l | \
    xargs -I {} printf "${GREEN}      ✓ 已签名 {} 个文件${NC}\n"

printf "${GREEN}✓${NC} 动态库签名完成\n"
printf "\n"

# 步骤 2: 签名应用包
printf "${BLUE}[2/3]${NC} 正在签名应用包...\n"
codesign --force --deep --sign - \
    --entitlements "$ENTITLEMENTS" \
    "$APP_PATH" 2>&1 | grep -q "replacing existing signature" && \
    printf "${GREEN}✓${NC} 应用包签名完成\n" || \
    printf "${GREEN}✓${NC} 应用包签名完成 (新签名)\n"
printf "\n"

# 步骤 3: 移除隔离属性
printf "${BLUE}[3/3]${NC} 正在移除隔离属性...\n"
xattr -cr "$APP_PATH" 2>&1
printf "${GREEN}✓${NC} 隔离属性已移除\n"
printf "\n"

# 验证签名
printf "${BLUE}验证签名状态...${NC}\n"
SIGNATURE_INFO=$(codesign -dvvv "$APP_PATH" 2>&1)

if echo "$SIGNATURE_INFO" | grep -q "Signature=adhoc"; then
    printf "${GREEN}✓${NC} 签名类型: adhoc (开发模式)\n"
else
    printf "${YELLOW}⚠${NC}  签名类型未知\n"
fi

# 检查 entitlements (需要单独命令)
ENTITLEMENTS_INFO=$(codesign -d --entitlements :- "$APP_PATH" 2>&1)
if echo "$ENTITLEMENTS_INFO" | grep -q "com.apple.security.cs.disable-library-validation"; then
    printf "${GREEN}✓${NC} Library Validation: 已禁用 (正确)\n"
else
    printf "${RED}✗${NC} Library Validation: 未检测到 entitlements\n"
fi

printf "\n"
printf "${BLUE}================================================${NC}\n"
printf "${GREEN}🎉 签名修复完成!${NC}\n"
printf "${BLUE}================================================${NC}\n"
printf "\n"
printf "现在可以通过以下方式启动应用:\n"
printf "  1. 双击 Finder 中的 ${GREEN}iDO.app${NC}\n"
printf "  2. 运行: ${YELLOW}open \"%s\"${NC}\n" "$APP_PATH"
printf "\n"
printf "${YELLOW}注意: 每次重新构建后需要重新运行此脚本${NC}\n"
printf "\n"
