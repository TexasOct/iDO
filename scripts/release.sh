#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() { echo -e "${RED}Error: $1${NC}" >&2; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${NC}$1${NC}"; }

# Parse command line arguments
RELEASE_TYPE=""
DRY_RUN=false
SKIP_PUSH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --major|--minor|--patch)
            RELEASE_TYPE="${1#--}"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-push)
            SKIP_PUSH=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./scripts/release.sh [--major|--minor|--patch] [--dry-run] [--skip-push]"
            echo ""
            echo "Options:"
            echo "  --major     Create a major release (X.0.0)"
            echo "  --minor     Create a minor release (0.X.0)"
            echo "  --patch     Create a patch release (0.0.X)"
            echo "  --dry-run   Run without making any changes"
            echo "  --skip-push Skip pushing to remote (for testing)"
            echo "  -h, --help  Show this help message"
            echo ""
            echo "If no release type is specified, standard-version will determine it automatically."
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

print_info "=========================================="
print_info "  Ido Release Script"
print_info "=========================================="
echo ""

# 1. Check current branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_error "Must be on main branch to release"
    print_info "Current branch: $CURRENT_BRANCH"
    exit 1
fi
print_success "On main branch"

# 2. Check working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    print_error "Working directory is not clean"
    git status --short
    exit 1
fi
print_success "Working directory is clean"

# 3. Fetch and check sync with remote
print_info "Fetching from remote..."
git fetch origin

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
    print_error "Local main is not up to date with origin/main"
    print_info "Local:  $LOCAL_HASH"
    print_info "Remote: $REMOTE_HASH"
    print_info "Run: git pull origin main"
    exit 1
fi
print_success "In sync with origin/main"

echo ""
print_info "------------------------------------------"
print_info "Pre-flight checks passed!"
print_info "------------------------------------------"
echo ""

# 4. Show current version
CURRENT_VERSION=$(node -p "require('./package.json').version")
print_info "Current version: v$CURRENT_VERSION"
echo ""

# 5. Build standard-version command
RELEASE_CMD="npx standard-version"
if [ -n "$RELEASE_TYPE" ]; then
    RELEASE_CMD="$RELEASE_CMD --release-as $RELEASE_TYPE"
fi
if [ "$DRY_RUN" = true ]; then
    RELEASE_CMD="$RELEASE_CMD --dry-run"
fi

# 6. Run standard-version
print_info "Running: $RELEASE_CMD"
echo ""

if ! eval $RELEASE_CMD; then
    print_error "Release command failed"
    exit 1
fi

echo ""

if [ "$DRY_RUN" = true ]; then
    print_warning "Dry run completed - no changes were made"
    exit 0
fi

# 7. Sync version to pyproject.toml
print_info "Syncing version to pyproject.toml..."
if node scripts/sync-pyproject-version.cjs; then
    # Add pyproject.toml to the commit
    git add pyproject.toml
    git commit --amend --no-edit
    print_success "Version synced to pyproject.toml"
else
    print_warning "Failed to sync pyproject.toml (non-critical)"
fi

echo ""

# 8. Get new version
NEW_VERSION=$(node -p "require('./package.json').version")
print_success "Version bumped: v$CURRENT_VERSION → v$NEW_VERSION"

# 9. Verify and update tag
TAG_NAME="v$NEW_VERSION"

# Move tag to amended commit (since we added pyproject.toml)
if git tag -d "$TAG_NAME" 2>/dev/null; then
    git tag -a "$TAG_NAME" -m "chore(release): $NEW_VERSION"
    print_success "Tag $TAG_NAME updated to include pyproject.toml"
fi

TAG_HASH=$(git rev-parse "$TAG_NAME" 2>/dev/null || echo "")

if [ -z "$TAG_HASH" ]; then
    print_error "Tag $TAG_NAME was not created"
    exit 1
fi

if ! git merge-base --is-ancestor "$TAG_HASH" HEAD; then
    print_error "Tag $TAG_NAME is not on main branch"
    exit 1
fi

print_success "Tag $TAG_NAME created at $(git rev-parse --short $TAG_HASH)"

echo ""
print_info "------------------------------------------"
print_info "Release $TAG_NAME ready!"
print_info "------------------------------------------"
echo ""

# 9. Push to remote
if [ "$SKIP_PUSH" = true ]; then
    print_warning "Skipping push (--skip-push flag)"
    print_info ""
    print_info "To push manually, run:"
    print_info "  git push origin main --follow-tags"
else
    print_info "Pushing to remote..."

    if git push origin main --follow-tags; then
        print_success "Pushed to origin/main with tags"
        echo ""
        print_success "🎉 Release $TAG_NAME completed successfully!"
    else
        print_error "Failed to push to remote"
        print_info "You may need to push manually:"
        print_info "  git push origin main --follow-tags"
        exit 1
    fi
fi

echo ""
print_info "Next steps:"
print_info "  1. Create GitHub release at: https://github.com/YOUR_ORG/YOUR_REPO/releases/new?tag=$TAG_NAME"
print_info "  2. Run bundle: pnpm bundle"
print_info "  3. Upload bundle artifacts to the release"
