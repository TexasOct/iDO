# Git Commit Convention Quick Reference

## Format

```
<type>(<scope>): <subject>
```

## Type Categories

| Type       | Description                       | Example                                    |
| ---------- | --------------------------------- | ------------------------------------------ |
| `feat`     | New feature                       | `feat(chat): add voice input support`      |
| `fix`      | Bug fix                           | `fix(api): handle null response from LLM`  |
| `docs`     | Documentation update              | `docs: update installation guide`          |
| `style`    | Code style (no functional change) | `style(ui): apply shadcn design system`    |
| `refactor` | Code refactoring                  | `refactor(db): simplify query logic`       |
| `perf`     | Performance improvement           | `perf(activity): cache event summaries`    |
| `test`     | Add or update tests               | `test(chat): add unit tests for streaming` |
| `build`    | Build system or dependencies      | `build: upgrade to vite 7`                 |
| `ci`       | CI/CD changes                     | `ci: add github actions workflow`          |
| `chore`    | Other miscellaneous changes       | `chore: update dependencies`               |
| `revert`   | Revert previous commit            | `revert: rollback commit abc123`           |

## Scope (Optional)

Common scopes: `frontend`, `backend`, `ui`, `api`, `chat`, `activity`, `agents`, `settings`, `db`, `deps`

## Examples

```bash
# ✅ Good examples
feat(chat): add activity context integration
fix(activity): resolve timeline rendering issue
docs: add commit convention guide
refactor(ui): migrate to shadcn components
perf(db): optimize activity query performance

# ❌ Bad examples
update code
fix bug
WIP
asdfgh
Fixed the thing
```

## Rules

- ✅ Use lowercase
- ✅ Use present tense ("add" not "added")
- ✅ Keep under 100 characters
- ✅ No period at the end
- ❌ No uppercase letters at start
- ❌ No vague descriptions

## Tools

```bash
# Commit messages are automatically validated
git commit -m "feat(scope): your message"

# Generate changelog
pnpm release
```
