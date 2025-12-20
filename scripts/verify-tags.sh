#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_error() { echo -e "${RED}❌ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

echo "Verifying all tags are on main branch..."
echo ""

ALL_GOOD=true
TAG_LIST=$(git tag -l "v*" | sort -V)

if [ -z "$TAG_LIST" ]; then
    print_warning "No version tags found"
    exit 0
fi

for tag in $TAG_LIST; do
    TAG_HASH=$(git rev-parse $tag 2>/dev/null)
    TAG_SHORT=$(git rev-parse --short $tag)
    TAG_MSG=$(git log -1 --format=%s $tag)

    # Check if tag is ancestor of main
    if git merge-base --is-ancestor $TAG_HASH main 2>/dev/null; then
        print_success "$tag ($TAG_SHORT) - $TAG_MSG"
    else
        print_error "$tag ($TAG_SHORT) is NOT on main branch - $TAG_MSG"
        ALL_GOOD=false
    fi
done

echo ""

if [ "$ALL_GOOD" = true ]; then
    print_success "All tags are correctly on main branch!"
    exit 0
else
    print_error "Some tags are not on main branch"
    echo ""
    echo "To fix misaligned tags, run:"
    echo "  ./scripts/fix-tags.sh"
    exit 1
fi
