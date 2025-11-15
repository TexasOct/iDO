# Troubleshooting Guide

Common issues and solutions for iDO development and deployment.

## Installation Issues

### Python Virtual Environment Fails

**Problem**: `uv sync` fails or modules not found

**Solutions**:

```bash
# 1. Remove and recreate virtual environment
rm -rf .venv
uv sync

# 2. Verify Python version
python --version  # Must be ≥ 3.14

# 3. Check uv installation
uv --version

# 4. Manual venv creation
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

### Node Modules Installation Fails

**Problem**: `pnpm install` fails

**Solutions**:

```bash
# 1. Clear pnpm cache
pnpm store prune

# 2. Remove node_modules and lockfile
rm -rf node_modules pnpm-lock.yaml

# 3. Reinstall
pnpm install

# 4. Try with legacy peer deps (if conflicts)
pnpm install --legacy-peer-deps
```

### Rust Compilation Errors

**Problem**: Tauri fails to compile

**Solutions**:

```bash
# 1. Update Rust toolchain
rustup update stable

# 2. Clean cargo cache
cargo clean

# 3. Clean project build
pnpm clean

# 4. Rebuild from scratch
pnpm setup
pnpm tauri build
```

## Development Issues

### TypeScript Client Not Updating

**Problem**: Backend changes not reflected in frontend types

**Solutions**:

```bash
# 1. Regenerate backend
pnpm setup-backend

# 2. Restart dev server
pnpm tauri:dev:gen-ts

# 3. Check handler is imported
# Edit backend/handlers/__init__.py
# Ensure your module is imported

# 4. Clean and rebuild
rm -rf src/lib/client/*
pnpm setup-backend
```

### Backend Changes Not Reflected

**Problem**: Python code changes don't take effect

**Solutions**:

```bash
# 1. Restart Tauri app
# Stop and re-run: pnpm tauri dev

# 2. Use FastAPI for faster iteration
uvicorn app:app --reload

# 3. Check Python cache
find . -type d -name __pycache__ -exec rm -rf {} +

# 4. Verify virtual environment
which python  # Should point to .venv/bin/python
```

### i18n Validation Errors

**Problem**: `pnpm check-i18n` reports errors

**Solutions**:

```bash
# 1. Run validation to see specific errors
pnpm check-i18n

# 2. Common fixes:
# - Add missing keys to zh-CN.ts
# - Remove extra keys from zh-CN.ts
# - Match structure (object vs string)

# 3. Example error:
# "Missing key: myFeature.title in zh-CN"
# → Add to src/locales/zh-CN.ts:
#   myFeature: { title: '...' }
```

## Runtime Issues

### No Events Being Captured

**Problem**: Dashboard shows 0 events

**Causes & Solutions**:

1. **Permissions not granted** (macOS/Linux)
   ```bash
   # macOS: System Settings → Privacy & Security
   # Grant Accessibility and Screen Recording permissions
   ```

2. **Perception layer not running**
   ```bash
   # Check in Dashboard → System Status
   # Should show "Running"
   
   # Try restarting
   # In app: Settings → Stop Monitoring → Start Monitoring
   ```

3. **Capture interval too long**
   ```toml
   # Edit backend/config/config.toml
   [monitoring]
   capture_interval = 1  # Try lower value
   ```

### LLM Connection Failed

**Problem**: "Test Connection" fails in settings

**Solutions**:

1. **Verify API key**
   ```bash
   # Check key is correct
   # Ensure no extra spaces
   ```

2. **Test manually**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer YOUR_API_KEY"
   ```

3. **Check network**
   ```bash
   # Ensure internet connection
   # Check firewall settings
   # Try different network
   ```

4. **Try different endpoint**
   ```bash
   # If using custom endpoint
   # Verify URL is correct
   # Check endpoint is reachable
   ```

### Screenshots Not Saving

**Problem**: No images in activity details

**Solutions**:

1. **Check permissions** (macOS)
   ```bash
   # System Settings → Privacy & Security → Screen Recording
   # Enable for iDO
   ```

2. **Verify save path**
   ```bash
   # Check path exists and is writable
   ls -la ~/.config/ido/screenshots/
   
   # Create if missing
   mkdir -p ~/.config/ido/screenshots/
   ```

3. **Check disk space**
   ```bash
   df -h
   ```

4. **Enable at least one monitor**
   ```bash
   # Settings → Screen Capture
   # Toggle on at least one monitor
   ```

### Database Errors

**Problem**: SQLite errors or corruption

**Solutions**:

```bash
# 1. Check database integrity
sqlite3 ~/.config/ido/ido.db "PRAGMA integrity_check;"

# 2. Backup and recreate
mv ~/.config/ido/ido.db ~/.config/ido/ido.db.backup
# Restart app to create new database

# 3. Restore from backup (if needed)
cp ~/.config/ido/ido.db.backup ~/.config/ido/ido.db
```

## Build Issues

### Production Build Fails

**Problem**: `pnpm tauri build` fails

**Solutions**:

```bash
# 1. Clean build artifacts
pnpm clean

# 2. Verify all checks pass
pnpm format
pnpm lint
pnpm tsc
uv run ty check
pnpm check-i18n

# 3. Check build logs
# Look for specific error message
# Usually points to the issue

# 4. Platform-specific issues
# macOS: Check code signing certificates
# Windows: Check Visual Studio Build Tools
# Linux: Check build dependencies
```

### macOS Code Signing Fails

**Problem**: Signing errors on macOS

**Solutions**:

```bash
# 1. Check certificates
security find-identity -v -p codesigning

# 2. Set environment variables
export APPLE_CERTIFICATE="Developer ID Application: ..."
export APPLE_ID="your@email.com"
export APPLE_PASSWORD="app-specific-password"

# 3. Use manual signing
pnpm tauri build
codesign --force --deep --sign "Developer ID" ./target/release/bundle/macos/iDO.app

# 4. See detailed guide
# docs/deployment/macos-signing.md
```

## Performance Issues

### High CPU Usage

**Problem**: iDO using excessive CPU

**Solutions**:

```bash
# 1. Reduce capture interval
# Edit backend/config/config.toml
[monitoring]
capture_interval = 2  # Increase from 1 to 2 seconds

# 2. Disable screenshot capture temporarily
# Settings → Screen Capture → Disable all monitors

# 3. Check for runaway processes
# Activity Monitor (macOS) or Task Manager (Windows)
```

### High Memory Usage

**Problem**: Memory usage grows over time

**Solutions**:

```bash
# 1. Reduce window size
# Edit backend/config/config.toml
[monitoring]
window_size = 20  # Keep at default

# 2. Enable image optimization
# Settings → Screenshot Settings
# Enable "Smart Deduplication"

# 3. Clear old data
# Settings → Advanced → Clear Old Data
```

### Slow UI

**Problem**: Frontend feels sluggish

**Solutions**:

```typescript
// 1. Use React DevTools Profiler
// Identify slow components

// 2. Check Zustand selectors
// Use specific selectors instead of whole store
const name = useStore(state => state.user.name)  // Good
const store = useStore()  // Bad (re-renders on any change)

// 3. Check for unnecessary re-renders
// Add React.memo to expensive components

// 4. Use virtual scrolling
// Already implemented in StickyTimelineGroup
```

## Platform-Specific Issues

### macOS Permission Dialogs Not Appearing

**Problem**: No permission prompts on first run

**Solutions**:

```bash
# 1. Reset privacy database
tccutil reset Accessibility
tccutil reset ScreenCapture

# 2. Restart app
# Prompts should appear now

# 3. Manual grant
# System Settings → Privacy & Security
# Add iDO to Accessibility and Screen Recording
```

### Windows Antivirus Blocking

**Problem**: Antivirus flags iDO

**Solutions**:

```powershell
# 1. Add exception for iDO
# Windows Security → Virus & threat protection
# Manage settings → Add or remove exclusions
# Add: C:\Path\To\iDO

# 2. Common false positives
# - Keyboard monitoring
# - Screen capture
# These are legitimate features, not malware
```

### Linux X11/Wayland Issues

**Problem**: Capture not working on Linux

**Solutions**:

```bash
# 1. Check display server
echo $XDG_SESSION_TYPE  # x11 or wayland

# 2. For Wayland, some features may be limited
# Try running in X11 mode

# 3. Check permissions
sudo usermod -a -G input $USER
# Logout and login again
```

## Getting More Help

### Check Logs

```bash
# Application logs
tail -f ~/.config/ido/logs/app.log

# Backend logs
tail -f ~/.config/ido/logs/backend.log

# Error logs
tail -f ~/.config/ido/logs/error.log
```

### Debug Mode

```bash
# Run in debug mode for verbose output
RUST_LOG=debug pnpm tauri dev

# Python debug logging
export LOG_LEVEL=DEBUG
```

### Report an Issue

When reporting bugs, include:

1. **System information**
   - OS and version
   - Python version (`python --version`)
   - Node version (`node --version`)
   - Rust version (`rustc --version`)

2. **Steps to reproduce**
   - What you did
   - What you expected
   - What actually happened

3. **Logs**
   - Relevant log excerpts
   - Error messages
   - Stack traces

4. **Screenshots**
   - If UI-related

📝 **[Create an issue →](https://github.com/TexasOct/iDO/issues)**

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Module not found` | Python import error | Run `pnpm setup-backend` |
| `Command not found` | Missing tool | Install prerequisite |
| `Permission denied` | macOS permissions | Grant in System Settings |
| `Database locked` | Concurrent access | Restart app |
| `API key invalid` | Wrong/expired key | Update in Settings |
| `Type error` | TypeScript issue | Run `pnpm tsc` |
| `Unknown variant` | Pydantic validation | Check request model |

---

**Still stuck?** Ask in [GitHub Discussions](https://github.com/TexasOct/iDO/discussions)
