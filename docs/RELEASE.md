# Release Process

This document describes the release process for Ido, designed to work with GitHub branch protection rules.

## Prerequisites

- Clean working directory
- Up-to-date with `origin/main`
- GitHub CLI (`gh`) installed and authenticated

## Release Commands

### PR-Based Release (Recommended)

For repositories with branch protection (requires PR before merging to main):

```bash
# Create a minor release (0.X.0) - most common
pnpm release:pr:minor

# Create a major release (X.0.0)
pnpm release:pr:major

# Create a patch release (0.0.X)
pnpm release:pr:patch

# Automatic version bump (based on commits)
pnpm release:pr

# Dry run (preview changes without creating PR)
pnpm release:pr:dry-run
```

### Direct Release (For repos without branch protection)

```bash
pnpm release:minor  # 0.X.0
pnpm release:major  # X.0.0
pnpm release:patch  # 0.0.X
pnpm release        # Auto-detect
pnpm release:dry-run
```

## Workflow: PR-Based Release

### 1. Start Release

Run the appropriate release command:

```bash
pnpm release:pr:minor
```

The script will:

- ✅ Verify you're on `main` branch
- ✅ Check working directory is clean
- ✅ Fetch and sync with remote
- 🌿 Create release branch (e.g., `release/v0.2.4-minor`)
- 📝 Run `standard-version` to:
  - Bump version in all config files
  - Update CHANGELOG.md
  - Create git commit
  - Create git tag
- 🚀 Push release branch and tag to remote
- 📋 Create Pull Request with changelog

### 2. Review PR

The created PR will include:

- Version bump changes
- Updated CHANGELOG.md
- Automatic changelog extraction in PR description

Review the changes and ensure:

- [ ] CHANGELOG.md is accurate
- [ ] Version bump is correct
- [ ] All CI checks pass

### 3. Merge PR

Once approved, merge the PR using GitHub's merge button (not command line).

### 4. Create GitHub Release

After the PR is merged:

1. Navigate to: `https://github.com/YOUR_ORG/YOUR_REPO/releases/new?tag=vX.X.X`
2. Click "Generate release notes" to auto-populate from commits
3. The CHANGELOG.md will be automatically included
4. Publish the release

### 5. Build and Upload Artifacts

```bash
# Build the application
pnpm bundle

# Sign macOS build (if on macOS)
pnpm sign-macos
```

Then upload the artifacts from `src-tauri/target/bundle-release/bundle/` to the GitHub release.

## Files Updated by Release

The release script automatically updates versions in:

- `package.json`
- `src-tauri/tauri.conf.json`
- `src-tauri/tauri.macos.conf.json`
- `src-tauri/tauri.windows.conf.json`
- `pyproject.toml`
- `CHANGELOG.md`

## CHANGELOG Format

The CHANGELOG follows [Conventional Commits](https://www.conventionalcommits.org/) and groups changes by type:

- ✨ **Features** - New features (`feat:`)
- 🐛 **Bug Fixes** - Bug fixes (`fix:`)
- ⚡ **Performance** - Performance improvements (`perf:`)
- ♻️ **Refactoring** - Code refactoring (`refactor:`)

Hidden types (not shown in CHANGELOG):

- 📝 Documentation (`docs:`)
- 💄 Styles (`style:`)
- ✅ Tests (`test:`)
- 📦 Build (`build:`)
- 👷 CI/CD (`ci:`)
- 🔧 Chores (`chore:`)

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
pnpm release:pr:patch  # or pnpm release:patch for direct release
```

## Troubleshooting

### Release branch already exists

```bash
git branch -D release/vX.X.X-type
git push origin --delete release/vX.X.X-type
```

### Tag already exists

```bash
# Delete local tag
git tag -d vX.X.X

# Delete remote tag
git push origin :refs/tags/vX.X.X
```

### PR creation failed

If `gh` CLI fails, create the PR manually:

1. Push the release branch
2. Go to GitHub and create PR from `release/vX.X.X-type` to `main`
3. Add the "release" label

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

## Best Practices

1. **Use descriptive commit messages** following Conventional Commits format
2. **Test before releasing** - Ensure all tests pass
3. **Review CHANGELOG** - Make sure auto-generated content is accurate
4. **Follow semver** - Choose the right release type:
   - **Major**: Breaking changes
   - **Minor**: New features (backwards compatible)
   - **Patch**: Bug fixes (backwards compatible)

## Why PR-based Release?

This workflow is designed for repositories with branch protection rules that require:

- Pull request reviews before merging
- Status checks to pass
- No direct pushes to main

Benefits:

- ✅ Enforces code review even for releases
- ✅ Allows CI/CD checks on release changes
- ✅ Creates audit trail through PR
- ✅ Prevents accidental direct pushes to main

## Verification Scripts

### Verify All Tags

Check that all tags are on main branch:

```bash
bash scripts/verify-tags.sh
```

## References

- [standard-version](https://github.com/conventional-changelog/standard-version) - Automated versioning and CHANGELOG
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit message convention
- [Semantic Versioning](https://semver.org/) - Version numbering scheme
