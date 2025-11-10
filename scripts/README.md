# iDO Scripts Organization

This directory contains build, setup, and development scripts organized by platform.

## Directory Structure

```
scripts/
├── unix/              # Unix-based systems (macOS, Linux)
├── windows/           # Windows-specific scripts
├── cross-platform/    # Platform-agnostic scripts
└── README.md          # This file
```

## Platform-Specific Scripts

### Unix Scripts (`unix/`)

Scripts for macOS and Linux systems using Bash.

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup-env.sh` | Initialize development environment | `pnpm setup` |
| `build-bundle.sh` | Build production bundle | `pnpm bundle` |
| `clean-build.sh` | Clean build artifacts | `pnpm clean` |
| `tauri-dev-gen-ts` | Start Tauri dev with TypeScript generation | `pnpm tauri:dev:gen-ts` |
| `sign-macos.sh` | Sign macOS application bundle | `pnpm sign-macos` |
| `fix-app-launch.sh` | Fix macOS app launch issues | Direct execution |
| `pytauri_env_init.sh` | Initialize PyTauri environment | Sourced by other scripts |

**Platform Requirements:**
- Bash shell (4.0+)
- macOS 11+ or Linux with systemd
- Execute permissions (`chmod +x script.sh`)

### Windows Scripts (`windows/`)

Scripts for Windows systems using PowerShell.

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup-env.ps1` | Initialize development environment | `pnpm setup:win` |
| `build-bundle.ps1` | Build production bundle | `pnpm bundle:win` |
| `tauri-dev-gen-ts.ps1` | Start Tauri dev with TypeScript generation | `pnpm tauri:dev:gen-ts:win` |
| `tauri-dev-win.ps1` | Start Tauri dev server | `pnpm tauri:dev:win` |

**Platform Requirements:**
- PowerShell 5.1+ or PowerShell Core 7+
- Windows 10/11
- Execution policy set appropriately

**Note:** All Windows scripts use `-ExecutionPolicy Bypass` flag in package.json to avoid permission issues.

### Cross-Platform Scripts (`cross-platform/`)

Scripts that work on all platforms (typically TypeScript/Node.js).

| Script | Purpose | Usage |
|--------|---------|-------|
| `check-i18n-keys.ts` | Validate translation key consistency | `pnpm check-i18n` |

**Platform Requirements:**
- Node.js 18+
- TypeScript runtime (`tsx`)

## Quick Reference

### Initial Setup

**macOS/Linux:**
```bash
pnpm setup
```

**Windows:**
```powershell
pnpm setup:win
```

### Development

**Start Development Server (with TypeScript client generation):**

macOS/Linux:
```bash
pnpm tauri:dev:gen-ts
```

Windows:
```powershell
pnpm tauri:dev:gen-ts:win
```

**Start Development Server (basic):**

macOS/Linux:
```bash
pnpm tauri:dev
```

Windows:
```powershell
pnpm tauri:dev:win
```

### Build

**Production Build:**

macOS/Linux:
```bash
pnpm bundle
```

Windows:
```powershell
pnpm bundle:win
```

**Signed macOS Build:**
```bash
pnpm tauri:build:signed
```

### Maintenance

**Clean Build Artifacts:**

macOS/Linux:
```bash
pnpm clean
```

Windows:
```powershell
# Use Git Bash or WSL
bash scripts/unix/clean-build.sh
```

**Validate Translations:**
```bash
pnpm check-i18n
```

## Development Workflow

### First-Time Setup

1. Clone repository
2. Run platform-specific setup:
   - **macOS/Linux:** `pnpm setup`
   - **Windows:** `pnpm setup:win`
3. Verify i18n: `pnpm check-i18n`

### Daily Development

1. Start dev server: `pnpm tauri:dev:gen-ts` (or `:win` on Windows)
2. Make changes
3. Format code: `pnpm format`
4. Check formatting: `pnpm lint`
5. Validate translations: `pnpm check-i18n`

### Building for Release

1. Clean previous builds: `pnpm clean`
2. Run platform-specific bundle:
   - **macOS:** `pnpm tauri:build:signed` (includes code signing)
   - **Windows:** `pnpm bundle:win`
   - **Linux:** `pnpm bundle`

## Script Maintenance

### Adding a New Script

1. **Determine Platform:**
   - Unix-only (Bash) → `unix/`
   - Windows-only (PowerShell) → `windows/`
   - Platform-agnostic (Node.js/TS) → `cross-platform/`

2. **Create Script:**
   - Unix: `touch scripts/unix/my-script.sh && chmod +x scripts/unix/my-script.sh`
   - Windows: `New-Item scripts/windows/my-script.ps1`
   - Cross-platform: `touch scripts/cross-platform/my-script.ts`

3. **Update package.json:**
   ```json
   "scripts": {
     "my-task": "bash scripts/unix/my-script.sh",
     "my-task:win": "powershell -ExecutionPolicy Bypass -File scripts/windows/my-script.ps1"
   }
   ```

4. **Document in this README**

### Porting Scripts Between Platforms

When a Unix script needs a Windows equivalent:

1. Create PowerShell version in `windows/`
2. Maintain same functionality
3. Add `:win` suffix to npm script name
4. Update this README

## Common Issues

### Unix: Permission Denied

```bash
chmod +x scripts/unix/*.sh
```

### Windows: Execution Policy Error

Use `-ExecutionPolicy Bypass` flag (already set in package.json):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/my-script.ps1
```

Or temporarily set policy:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Cross-Platform: tsx not found

```bash
pnpm install
```

## Best Practices

1. **Keep scripts focused:** One script = one purpose
2. **Use descriptive names:** `setup-env.sh` not `setup.sh`
3. **Document parameters:** Add comments for required arguments
4. **Handle errors:** Exit with non-zero status on failure
5. **Platform-specific only when necessary:** Prefer cross-platform scripts when possible
6. **Test on target platform:** Windows scripts tested on Windows, etc.

## Related Documentation

- [Development Guide](../docs/development.md)
- [Python Environment](../docs/python_environment.md)
- [Architecture Overview](../docs/architecture.md)
