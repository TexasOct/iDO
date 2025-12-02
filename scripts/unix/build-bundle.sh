#!/usr/bin/env bash
set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
PYTHON_VERSION="3.14.0+20251014"


# Print colored information
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

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

info "Project root directory: $PROJECT_ROOT"

# Detect operating system and architecture
OS=$(uname -s)
ARCH=$(uname -m)

info "Operating system: $OS"
info "Architecture: $ARCH"

# Determine Python download URL and path based on system
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
        error "Unsupported operating system: $OS"
        ;;
esac

# Step 1: Download and extract portable Python
info "Step 1/4: Preparing portable Python environment..."

if [ ! -d "src-tauri/pyembed/python" ]; then
    info "Downloading Python: $PYTHON_FILE"

    mkdir -p src-tauri/pyembed
    cd src-tauri/pyembed

    if [ ! -f "$PYTHON_FILE" ]; then
        curl -L -o "$PYTHON_FILE" "$PYTHON_URL" || error "Python download failed"
    fi

    info "Extracting Python..."
    tar -xzf "$PYTHON_FILE" || error "Extraction failed"

    # Clean up archive
    rm -f "$PYTHON_FILE"

    cd "$PROJECT_ROOT"
    success "Python environment prepared"
else
    success "Python environment already exists, skipping download"
fi

# Verify Python executable
if [ ! -f "$PYTHON_BIN" ]; then
    error "Python executable does not exist: $PYTHON_BIN"
fi

# macOS specific: Fix libpython install_name
if [ "$OS" = "Darwin" ] && [ -d "$LIBPYTHON_DIR" ]; then
    info "Fixing libpython install_name..."
    LIBPYTHON=$(find "$LIBPYTHON_DIR" -name "libpython*.dylib" 2>/dev/null | head -1)
    if [ -f "$LIBPYTHON" ]; then
        LIBPYTHON_NAME=$(basename "$LIBPYTHON")
        install_name_tool -id "@rpath/$LIBPYTHON_NAME" "$LIBPYTHON" || warning "Failed to fix install_name, may need manual fix"
        success "Fixed install_name for $LIBPYTHON_NAME"
    fi
fi

# Step 2: Install project to embedded Python environment
info "Step 2/4: Installing project to embedded Python environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    error "uv command not found, please install first: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

info "Installing dependencies with uv..."
PYTAURI_STANDALONE="1" uv pip install \
    --exact \
    --python="$PYTHON_BIN" \
    --reinstall-package=ido-app \
    . || error "Dependency installation failed"

success "Dependencies installed"

# Step 3: Configure build environment
info "Step 3/4: Configuring build environment..."

# Use realpath if available, otherwise fall back to read path
if command -v realpath >/dev/null 2>&1; then
    REAL_PY=$(realpath "$PYTHON_BIN")
else
    REAL_PY="$PYTHON_BIN"
fi
export PYO3_PYTHON="$REAL_PY"

# Configure RUSTFLAGS based on system
if [ "$OS" = "Linux" ]; then
    if [ -d "$LIBPYTHON_DIR" ]; then
        if command -v realpath >/dev/null 2>&1; then
            LIBPY_REAL=$(realpath "$LIBPYTHON_DIR")
        else
            LIBPY_REAL="$LIBPYTHON_DIR"
        fi
        export RUSTFLAGS="-C link-arg=-Wl,-rpath,\$ORIGIN/../lib/iDO/lib -L $LIBPY_REAL"
    else
        error "Python library directory does not exist: $LIBPYTHON_DIR"
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
        error "Python library directory does not exist: $LIBPYTHON_DIR"
    fi
fi

info "PYO3_PYTHON: $PYO3_PYTHON"
info "RUSTFLAGS: $RUSTFLAGS"

success "Environment configuration complete"

# helper: Find the latest generated .app (by modification time)
find_latest_app() {
    local target_dir="src-tauri/target"
    if [ ! -d "$target_dir" ]; then
        return 1
    fi

    # Use stat -f on macOS, stat -c on Linux
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

# Step 4: Execute bundling
info "Step 4/4: Starting application bundling..."

# On macOS we want to produce both a plain release .app and the bundle (installer) build.
if [ "$OS" = "Darwin" ]; then
    info "macOS: First build release app (for testing/running), then build bundle (for distribution)"

    # 4.1 Release build (default release profile)
    info "Building release application..."
    pnpm -- tauri build -- --profile release || error "Release bundling failed"

    RELEASE_APP=$(find_latest_app || true)
    if [ -n "$RELEASE_APP" ]; then
        success "Release application generated: $RELEASE_APP"
    else
        warning "Failed to locate release generated .app"
    fi

    # 4.2 Bundle build (using bundle config and bundle-release profile)
    info "Building bundle (installer)..."
    pnpm -- tauri build \
        --config="src-tauri/tauri.bundle.json" \
        -- --profile bundle-release || error "Bundle packaging failed"

    BUNDLE_APP=$(find_latest_app || true)
    if [ -n "$BUNDLE_APP" ]; then
        # If both bundle build and release build exist, returns the most recently modified one (usually bundle)
        success "Bundle generated .app (or package artifacts) generated: $BUNDLE_APP"
    else
        warning "Failed to locate bundle generated .app"
    fi
else
    # Non-macOS (Linux, etc.) build bundle profile as before
    pnpm -- tauri build \
        --config="src-tauri/tauri.bundle.json" \
        -- --profile bundle-release || error "Packaging failed"
    success "Packaging complete (non-macOS)"
fi

# Display packaging result location
info "Packaging result location:"
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

success "✨ Build complete!"
