#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() { echo -e "${RED}Error: $1${NC}" >&2; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Parse command line arguments
RELEASE_TYPE=""
DRY_RUN=false

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
        -h|--help)
            echo "Usage: ./scripts/release-pr.sh [--major|--minor|--patch] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --major     Create a major release (X.0.0)"
            echo "  --minor     Create a minor release (0.X.0)"
            echo "  --patch     Create a patch release (0.0.X)"
            echo "  --dry-run   Run without making any changes"
            echo "  -h, --help  Show this help message"
            echo ""
            echo "This script creates a release PR instead of pushing directly to main."
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
print_info "  Ido Release PR Script"
print_info "=========================================="
echo ""

# 1. Check current branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_error "Must be on main branch to start release"
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

# 3. Fetch and sync with remote
print_info "Fetching from remote..."
git fetch origin

# Check if local is behind remote
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)
MERGE_BASE=$(git merge-base HEAD origin/main)

if [ "$MERGE_BASE" != "$LOCAL_HASH" ]; then
    print_error "Local main is behind origin/main"
    print_info "Please run: git pull origin main"
    exit 1
fi
print_success "Local main is up to date"

echo ""
print_info "------------------------------------------"
print_info "Pre-flight checks passed!"
print_info "------------------------------------------"
echo ""

# 4. Show current version
CURRENT_VERSION=$(node -p "require('./package.json').version")
print_info "Current version: v$CURRENT_VERSION"

# 5. Determine release type if not specified
if [ -z "$RELEASE_TYPE" ]; then
    print_warning "No release type specified, standard-version will determine automatically"
    RELEASE_TYPE_STR="auto"
else
    RELEASE_TYPE_STR="$RELEASE_TYPE"
fi

# 6. Create release branch
RELEASE_BRANCH="release/v$CURRENT_VERSION-$RELEASE_TYPE_STR"
print_info "Creating release branch: $RELEASE_BRANCH"

if [ "$DRY_RUN" = false ]; then
    git checkout -b "$RELEASE_BRANCH"
    print_success "Created branch: $RELEASE_BRANCH"
else
    print_warning "[DRY RUN] Would create branch: $RELEASE_BRANCH"
fi

echo ""

# 7. Build standard-version command
RELEASE_CMD="npx standard-version"
if [ -n "$RELEASE_TYPE" ]; then
    RELEASE_CMD="$RELEASE_CMD --release-as $RELEASE_TYPE"
fi
if [ "$DRY_RUN" = true ]; then
    RELEASE_CMD="$RELEASE_CMD --dry-run"
fi

# 8. Run standard-version
print_info "Running: $RELEASE_CMD"
echo ""

if ! eval $RELEASE_CMD; then
    print_error "Release command failed"
    if [ "$DRY_RUN" = false ]; then
        print_info "Cleaning up release branch..."
        git checkout main
        git branch -D "$RELEASE_BRANCH"
    fi
    exit 1
fi

echo ""

if [ "$DRY_RUN" = true ]; then
    print_warning "Dry run completed - no changes were made"
    git checkout main
    git branch -D "$RELEASE_BRANCH" 2>/dev/null || true
    exit 0
fi

# 9. Sync version to pyproject.toml
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

# 10. Get new version
NEW_VERSION=$(node -p "require('./package.json').version")
print_success "Version bumped: v$CURRENT_VERSION → v$NEW_VERSION"

echo ""
print_info "------------------------------------------"
print_info "Release branch ready!"
print_info "------------------------------------------"
echo ""

# 11. Push release branch to remote (tag will be created after PR merge)
print_info "Pushing release branch to remote..."

if git push origin "$RELEASE_BRANCH"; then
    print_success "Pushed release branch"
else
    print_error "Failed to push to remote"
    print_info "You may need to push manually:"
    print_info "  git push origin $RELEASE_BRANCH"
    exit 1
fi

echo ""

# 12. Create PR
print_info "Creating pull request..."
echo ""

# Extract changelog for this version
CHANGELOG_CONTENT=$(node -p "
const fs = require('fs');
const content = fs.readFileSync('CHANGELOG.md', 'utf-8');
const lines = content.split('\\n');
let inVersion = false;
let result = [];
for (const line of lines) {
  if (line.startsWith('### [') || line.startsWith('## [')) {
    if (inVersion) break;
    if (line.includes('$NEW_VERSION')) {
      inVersion = true;
      continue;
    }
  }
  if (inVersion && line.trim()) {
    result.push(line);
  }
}
result.join('\\n').trim();
" 2>/dev/null || echo "See CHANGELOG.md for details")

PR_BODY="## Release v$NEW_VERSION

This PR contains the automated release for version $NEW_VERSION.

### Changes
$CHANGELOG_CONTENT

---

### Release Checklist
- [ ] Review CHANGELOG.md
- [ ] Verify version bump is correct
- [ ] All CI checks pass

After merging this PR:
- Tag \`v$NEW_VERSION\` will be automatically created on the merge commit
- GitHub Actions will trigger the release build workflow
- GitHub Release will be automatically created with build artifacts

---

🤖 Generated by release-pr.sh script"

if gh pr create \
    --title "release: v$NEW_VERSION" \
    --body "$PR_BODY" \
    --base main \
    --head "$RELEASE_BRANCH" \
    --label "release"; then

    print_success "🎉 Release PR created successfully!"
    echo ""
    PR_URL=$(gh pr view --json url -q .url)
    print_info "PR URL: $PR_URL"
else
    print_error "Failed to create PR using gh CLI"
    print_info "Please create PR manually at:"
    print_info "  https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/compare/main...$RELEASE_BRANCH"
    exit 1
fi

echo ""
print_info "Next steps:"
print_info "  1. Review and merge the PR: $PR_URL"
print_info "  2. After merge, the tag v$NEW_VERSION will be created automatically on main"
print_info "  3. GitHub Actions will trigger release build and create GitHub Release"
print_info "  4. Review the auto-generated release at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/releases"
echo ""

print_success "Release PR created! 🚀"
