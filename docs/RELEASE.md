# Release Process

This document describes the release process for Ido, including best practices to ensure tags are always created on the `main` branch.

## Quick Release

For a standard patch release:

```bash
./scripts/release.sh --patch
```

For minor or major releases:

```bash
./scripts/release.sh --minor  # 0.X.0
./scripts/release.sh --major  # X.0.0
```

For automatic version bump (based on commit messages):

```bash
./scripts/release.sh
```

## Release Policy

### Critical Rules

1. **Always release from `main` branch**
   - Never create tags on feature branches
   - Never rebase or cherry-pick after creating a tag

2. **Tag must point to the same commit on main**
   - If you rebase/cherry-pick a commit, the tag becomes invalid
   - Use `scripts/verify-tags.sh` to check tag consistency

3. **Use the release script**
   - The script enforces all safety checks
   - Ensures you're on main, in sync with remote, and working directory is clean

### Why This Matters

**Problem:** Tag pointing to wrong commit

```
v0.2.4 tag → ae676c7 (on feature branch)
main branch → e3eb595 (same commit message, different hash)
```

This happens when:

1. Create tag on feature branch
2. Rebase/cherry-pick to main
3. Tag still points to old commit (not on main)

**Solution:** Always create tags on main after merging

```bash
git checkout main
git merge feature-branch
./scripts/release.sh --patch
```

## Step-by-Step Release Process

### 1. Prepare Release

Ensure all changes are merged to main:

```bash
git checkout main
git pull origin main
```

Verify working directory is clean:

```bash
git status
```

### 2. Run Release Script

The script will:

- Verify you're on main branch
- Check working directory is clean
- Ensure in sync with origin/main
- Run `standard-version` to bump version and update CHANGELOG
- Create annotated tag on main
- Push to remote with tags

```bash
./scripts/release.sh --patch
```

Or for dry-run (no changes):

```bash
./scripts/release.sh --patch --dry-run
```

### 3. Verify Release

Check that tag was created correctly:

```bash
git log --oneline -5
git tag -l "v*" | tail -5
```

Verify tag is on main:

```bash
./scripts/verify-tags.sh
```

### 4. CI/CD Builds Release

GitHub Actions will automatically:

1. Verify tag is on main branch (fails if not)
2. Build macOS and Windows bundles
3. Create GitHub release with artifacts

Monitor the workflow at:
https://github.com/YOUR_ORG/YOUR_REPO/actions

### 5. Publish Release

1. Go to GitHub releases page
2. Edit the draft release created by CI
3. Add release notes if needed
4. Publish the release

## Manual Release (Not Recommended)

If you must release manually:

```bash
# 1. Update version in all files
vim package.json  # Update version
vim src-tauri/Cargo.toml  # Update version
vim pyproject.toml  # Update version

# 2. Update CHANGELOG
vim CHANGELOG.md

# 3. Commit changes
git add .
git commit -m "chore(release): X.Y.Z"

# 4. Create annotated tag
git tag -a vX.Y.Z -m "chore(release): X.Y.Z"

# 5. Push with tags
git push origin main --follow-tags
```

## Fixing Misaligned Tags

If tags are not on main (usually from old releases):

```bash
# Run the fix script
./scripts/fix-tags.sh

# Force push fixed tags (WARNING: team must be notified)
git push origin --tags --force
```

## Verification Scripts

### Verify All Tags

Check that all tags are on main branch:

```bash
./scripts/verify-tags.sh
```

### CI Tag Verification

The GitHub Actions workflow automatically verifies tags:

- On every tag push, checks if tag is on main
- Fails the build if tag is not on main
- See `.github/workflows/release.yml`

## Troubleshooting

### Tag Already Exists

If you need to move a tag:

```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push origin :refs/tags/vX.Y.Z

# Create new tag on correct commit
git tag -a vX.Y.Z COMMIT_HASH -m "chore(release): X.Y.Z"

# Push new tag
git push origin vX.Y.Z
```

### Tag Not on Main

This means the tag was created on a different branch. Fix it:

```bash
# Find the commit on main with same message
CORRECT_HASH=$(git log --oneline main | grep "X.Y.Z" | head -1 | awk '{print $1}')

# Move the tag
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
git tag -a vX.Y.Z $CORRECT_HASH -m "chore(release): X.Y.Z"
git push origin vX.Y.Z
```

### Version Mismatch

If package.json, Cargo.toml, and pyproject.toml have different versions:

```bash
# standard-version should sync them, but if not:
# Manually update all three files to match
vim package.json
vim src-tauri/Cargo.toml
vim pyproject.toml

git add .
git commit --amend --no-edit
git tag -f vX.Y.Z
git push origin main --force-with-lease
git push origin vX.Y.Z --force
```

## References

- [standard-version](https://github.com/conventional-changelog/standard-version) - Automated versioning and CHANGELOG
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit message convention
- [Semantic Versioning](https://semver.org/) - Version numbering scheme
