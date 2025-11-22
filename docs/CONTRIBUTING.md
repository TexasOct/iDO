# Contributing Guide

Thank you for considering contributing to the iDO project!

## Commit Convention

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification and uses commitlint to validate commit messages.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Type

Must be one of the following:

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes that affect the build system or external dependencies (example scopes: gulp, npm)
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

#### Scope

Optional, indicates the scope of the commit, for example:

- `frontend`: Frontend related
- `backend`: Backend related
- `ui`: UI components
- `api`: API related
- `chat`: Chat functionality
- `activity`: Activity tracking
- `agents`: Agent functionality
- `settings`: Settings
- `db`: Database
- `build`: Build system
- `deps`: Dependency updates

#### Subject

- Use imperative, present tense: "change" not "changed" nor "changes"
- Don't capitalize the first letter
- No period (.) at the end

#### Body

Optional, provides detailed explanation of the motivation and changes.

#### Footer

Optional, used to reference issues or note breaking changes:

```
BREAKING CHANGE: description of the breaking change

Closes #123
```

### Examples

#### New Feature

```bash
git commit -m "feat(chat): add activity context to chat conversations

- Load activity details and events when activity is linked
- Generate structured context for LLM
- Display activity context in chat UI

Closes #42"
```

#### Bug Fix

```bash
git commit -m "fix(activity): resolve asyncio.run() error in event loading

Replace asyncio.run() with await to fix event loop conflict"
```

#### Documentation Update

```bash
git commit -m "docs: add commit message guidelines"
```

#### Refactoring

```bash
git commit -m "refactor(ui): migrate to shadcn design system

- Update border radius from rounded-3xl to rounded-lg
- Replace custom opacity values with semantic colors
- Remove gradient backgrounds for cleaner design"
```

#### Performance Improvement

```bash
git commit -m "perf(activity): optimize event loading with batch queries"
```

## Development Workflow

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/ido.git
cd ido
```

### 2. Install Dependencies

```bash
pnpm setup-all
```

### 3. Create a Branch

```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/bug-description
```

### 4. Development and Testing

```bash
# Frontend development
pnpm dev

# Full app development
pnpm tauri:dev:gen-ts

# Type checking
pnpm tsc
uv run ty check

# Format code
pnpm format

# Check formatting
pnpm lint
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat(scope): your commit message"
```

The commit-msg hook will automatically validate your commit message.

### 6. Push Branch

```bash
git push origin feat/your-feature-name
```

### 7. Create Pull Request

Create a Pull Request on GitHub describing your changes.

## Release Process

The project uses `standard-version` to automatically generate CHANGELOG and version numbers.

### Automatic Version Release (Recommended)

```bash
# Automatically detect version type (patch/minor/major)
pnpm release

# Generates new version number, updates CHANGELOG, creates git tag
```

### Manual Version Type

```bash
# Release patch version (0.1.0 -> 0.1.1)
pnpm release:patch

# Release minor version (0.1.0 -> 0.2.0)
pnpm release:minor

# Release major version (0.1.0 -> 1.0.0)
pnpm release:major
```

### After Release

```bash
# Push commits and tags
git push --follow-tags origin main
```

## Code Standards

### TypeScript

- Run `pnpm tsc` to ensure no type errors
- Avoid using `any`, use specific types or `unknown`
- Prefer Protocol/Interface to define type contracts

### Python

- Run `uv run ty check` for type checking
- Use Protocol to define interfaces
- All SQL queries should be placed in `backend/core/sqls/queries.py`

### Styles

- Use Tailwind CSS
- Follow shadcn/ui design standards
- Run `pnpm format` to auto-format

### i18n

- Run `pnpm check-i18n` to check translation key consistency
- Ensure Chinese and English translation files are in sync

## Issue Reporting

When submitting an issue, please include:

1. Problem description
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. Environment information (OS, version, etc.)
6. Related logs or screenshots

## Code of Conduct

- Respect all contributors
- Provide constructive feedback
- Maintain professional and friendly communication

Thank you for your contribution! 🎉
