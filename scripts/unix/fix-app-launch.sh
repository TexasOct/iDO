#!/bin/bash
# ============================================================================
# iDO macOS Application Launch Fix Script
# ============================================================================
# Purpose: Fix immediate exit issue when launching app by double-clicking due to DYLD shared memory limitations
# Mechanism: Create launch wrapper script, set correct environment variables, bypass DYLD limitations
# Usage: ./scripts/fix-app-launch.sh [app-path]
# ============================================================================

set -e

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

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# Get application path
if [ -n "$1" ]; then
    APP_PATH="$1"
else
    # Default path
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    APP_PATH="$PROJECT_ROOT/src-tauri/target/bundle-release/bundle/macos/iDO.app"
fi

# Check if application exists
if [ ! -d "$APP_PATH" ]; then
    error "Application bundle does not exist: $APP_PATH"
fi

MACOS_DIR="$APP_PATH/Contents/MacOS"
RESOURCES_DIR="$APP_PATH/Contents/Resources"

echo ""
echo "=================================================="
echo "  iDO macOS Application Launch Fix Tool"
echo "=================================================="
echo ""
info "Application path: $APP_PATH"
echo ""

# Step 1: Backup original executable
info "Step 1/4: Backing up original executable..."

if [ -f "$MACOS_DIR/ido-app.bin" ]; then
    warning "Backup file already exists, skipping backup"
else
    if [ ! -f "$MACOS_DIR/ido-app" ]; then
        error "Executable does not exist: $MACOS_DIR/ido-app"
    fi

    mv "$MACOS_DIR/ido-app" "$MACOS_DIR/ido-app.bin"
    success "Backed up: ido-app → ido-app.bin"
fi

# Step 2: Create launch wrapper script
info "Step 2/4: Creating launch wrapper script..."

cat > "$MACOS_DIR/ido-app" << 'WRAPPER_EOF'
#!/bin/bash
# iDO Launch Wrapper Script
# Auto-generated, do not edit manually

# Get application directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RESOURCES_DIR="$APP_DIR/Resources"

# Optional: Enable logging (for debugging)
# Uncomment the following two lines to enable logging
# LOG_FILE="$HOME/ido_launch.log"
# exec 1>> "$LOG_FILE" 2>&1

# Optional: Debug output
# echo "=========================================="
# echo "iDO Launch: $(date)"
# echo "APP_DIR: $APP_DIR"
# echo "RESOURCES_DIR: $RESOURCES_DIR"
# echo "=========================================="

# Set Python environment variables
export PYTHONHOME="$RESOURCES_DIR"
export PYTHONPATH="$RESOURCES_DIR/lib/python3.14:$RESOURCES_DIR/lib/python3.14/site-packages"

# Set dynamic library path
export DYLD_LIBRARY_PATH="$RESOURCES_DIR/lib:$DYLD_LIBRARY_PATH"
export DYLD_FRAMEWORK_PATH="$RESOURCES_DIR:$DYLD_FRAMEWORK_PATH"

# Critical: Disable DYLD shared region loading to avoid memory mapping conflicts
# This is the core solution to 'DYLD unnest' warning and immediate app exit issue
export DYLD_SHARED_REGION_AVOID_LOADING=1

# Set working directory to application bundle root
cd "$APP_DIR"

# Run the actual executable
# Use exec to replace current process, avoiding extra process hierarchy
exec "$SCRIPT_DIR/ido-app.bin" "$@"
WRAPPER_EOF

chmod +x "$MACOS_DIR/ido-app"
success "Wrapper script created"

# Step 3: Re-sign application
info "Step 3/4: Re-signing application..."

# Sign wrapper script
codesign --force --sign - "$MACOS_DIR/ido-app" 2>&1 > /dev/null

# Sign original executable
codesign --force --sign - "$MACOS_DIR/ido-app.bin" 2>&1 > /dev/null

# Find entitlements file
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENTITLEMENTS="$PROJECT_ROOT/src-tauri/entitlements.plist"

if [ -f "$ENTITLEMENTS" ]; then
    # Sign entire application with entitlements
    codesign --force --deep --sign - \
        --entitlements "$ENTITLEMENTS" \
        "$APP_PATH" 2>&1 > /dev/null
    success "Signed with entitlements.plist"
else
    # Use default signature
    codesign --force --deep --sign - "$APP_PATH" 2>&1 > /dev/null
    warning "entitlements.plist not found, using default signature"
fi

# Step 4: Clear quarantine attributes
info "Step 4/4: Clearing quarantine attributes..."
xattr -cr "$APP_PATH" 2>&1 > /dev/null
success "Quarantine attributes cleared"

# Verify
echo ""
info "Verifying installation..."
echo "  - Original executable: $MACOS_DIR/ido-app.bin"
echo "  - Wrapper script: $MACOS_DIR/ido-app"
echo "  - Application bundle: $APP_PATH"

# Check signature
if codesign -dvvv "$APP_PATH" 2>&1 | grep -q "Signature=adhoc"; then
    success "Signature verification passed (adhoc mode)"
else
    warning "Signature verification failed"
fi

echo ""
echo "=================================================="
echo "  🎉 Fix Complete!"
echo "=================================================="
echo ""
echo "You can now launch the application by:"
echo "  1. Double-clicking iDO.app in Finder"
echo "  2. Running: open \"$APP_PATH\""
echo ""
echo "If you need to view launch logs (for debugging):"
echo "  1. Edit $MACOS_DIR/ido-app"
echo "  2. Uncomment LOG_FILE and exec redirect lines"
echo "  3. View logs: tail -f ~/ido_launch.log"
echo ""
success "All operations complete!"
