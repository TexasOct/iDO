# First Run Guide

This guide walks you through the initial setup and configuration of iDO after installation.

## Prerequisites

Make sure you've completed the [Installation Guide](./installation.md) first.

## Starting the Application

### Development Mode

For development, you have several options:

#### Option 1: Frontend Only (Fastest)
```bash
pnpm dev
```
- Starts React dev server at http://localhost:5173
- Hot module replacement (HMR) for instant updates
- Use when working on UI without backend changes

#### Option 2: Full Application (Recommended)
```bash
pnpm tauri:dev:gen-ts
```
- Starts complete desktop application
- Auto-generates TypeScript client from Python handlers
- Use when working on both frontend and backend

#### Option 3: Backend API Server
```bash
uvicorn app:app --reload
```
- Starts FastAPI server at http://localhost:8000
- Auto-generated API docs at http://localhost:8000/docs
- Use for testing backend endpoints independently

## Initial Configuration

### 1. Grant System Permissions (macOS/Linux)

On first run, iDO will request system permissions:

#### macOS
- **Accessibility**: Required to monitor keyboard and mouse events
- **Screen Recording**: Required to capture screenshots

The app will guide you through granting these permissions. See the detailed [Permissions Guide](../guides/features/permissions.md) for troubleshooting.

#### Linux
Permissions are typically granted automatically, but you may need to run:
```bash
# Add user to input group
sudo usermod -a -G input $USER
```

### 2. Configure LLM Provider

iDO requires an LLM provider for activity analysis:

1. Open **Settings** → **LLM Configuration**
2. Choose your provider:
   - OpenAI (recommended)
   - Compatible OpenAI API endpoints
3. Enter your API key
4. Select a model (e.g., `gpt-4` or `gpt-3.5-turbo`)
5. Click **Test Connection** to verify

**Privacy Note**: LLM calls are made with your API key. No data is sent to iDO servers.

### 3. Configure Screen Capture

Choose which monitors to capture:

1. Open **Settings** → **Screen Capture**
2. View detected monitors
3. Toggle monitors on/off
4. Click **Save**

By default, only the primary monitor is enabled.

### 4. Adjust Screenshot Settings (Optional)

Fine-tune screenshot behavior:

1. Open **Settings** → **Screenshot Settings**
2. Configure:
   - **Capture Interval**: How often to take screenshots (default: 1 second)
   - **Save Path**: Where to store screenshots (default: `~/.config/ido/screenshots`)
   - **Image Quality**: Balance between quality and disk space (default: 85%)
   - **Image Optimization**: Enable smart deduplication (recommended: enabled)

## Verify Everything Works

### 1. Check Perception Layer

```bash
# View real-time stats
# In the app: Dashboard → System Status
```

You should see:
- ✅ Keyboard events being captured
- ✅ Mouse events being captured
- ✅ Screenshots being taken

### 2. Test Processing Pipeline

1. Use your computer normally for 1-2 minutes
2. Navigate to **Activity Timeline**
3. You should see activities being created with:
   - Event titles and descriptions
   - Associated screenshots
   - Timestamps

### 3. Test Agent System

1. Open **Agents** view
2. Select an activity
3. Click **Generate Tasks**
4. Agents should analyze the activity and suggest tasks

## Understanding the Interface

### Dashboard
- System status and statistics
- Active model information
- Processing pipeline status

### Activity Timeline
- Chronological view of your activities
- Grouped by date with sticky headers
- Click any activity for details

### Agents
- AI-generated task recommendations
- Task priority and status
- Agent execution results

### Settings
- LLM configuration
- Screen capture preferences
- System permissions
- UI preferences (theme, language)

## Common First-Run Issues

### No Events Being Captured

**Symptoms**: Dashboard shows 0 events

**Solutions**:
1. Check system permissions are granted
2. Verify perception layer is running (Dashboard → System Status)
3. Restart the application

### LLM Connection Failed

**Symptoms**: "Test Connection" fails

**Solutions**:
1. Verify API key is correct
2. Check internet connection
3. Ensure API endpoint is reachable
4. Try a different model

### Screenshots Not Saving

**Symptoms**: No images in activity details

**Solutions**:
1. Check screen capture permissions (macOS)
2. Verify save path is writable
3. Ensure at least one monitor is enabled in settings
4. Check disk space

### Application Won't Start

**Symptoms**: Crash or error on startup

**Solutions**:
1. Check logs: `~/.config/ido/logs/`
2. Verify all dependencies installed: `pnpm setup`
3. Try clean build: `pnpm clean && pnpm tauri dev`
4. Check [Troubleshooting Guide](../deployment/troubleshooting.md)

## Next Steps

Now that iDO is running:

- 📖 Learn about [Development Workflows](./development-workflow.md)
- 🏗️ Understand the [Architecture](../architecture/README.md)
- 💻 Explore [Frontend Development](../guides/frontend/README.md)
- 🐍 Dive into [Backend Development](../guides/backend/README.md)

## Data and Privacy

### Where is Data Stored?

All data is stored locally:

- **Database**: `~/.config/ido/ido.db` (SQLite)
- **Screenshots**: `~/.config/ido/screenshots/` (configurable)
- **Logs**: `~/.config/ido/logs/`
- **Config**: `~/.config/ido/config.toml`

### What Gets Sent to LLM?

Only when processing activities:
- Screenshot images (as base64)
- Keyboard/mouse event summaries (no raw keystrokes)
- Timestamps and window titles

**No cloud storage** - Everything stays on your device except LLM API calls.

## Need Help?

- 📚 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/TexasOct/iDO/issues)
- 💬 [GitHub Discussions](https://github.com/TexasOct/iDO/discussions)
