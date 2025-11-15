# Features Overview

Learn about iDO's main features and how to use them effectively.

## 🎯 What is iDO?

iDO is a local-first AI desktop copilot that:

- **📊 Tracks your activity** - Monitors what you do on your computer
- **🤖 Summarizes with AI** - Uses LLMs to understand context
- **✅ Recommends tasks** - Suggests what to do next based on your patterns
- **🔒 Keeps data private** - Everything stays on your device

## Core Features

### 1. Activity Timeline

**What it does**: Automatically captures and organizes your computer activities

**How it works**:
- Monitors keyboard and mouse events
- Takes periodic screenshots
- Groups related events into activities
- Uses AI to generate descriptive titles

**How to use**:
1. Navigate to **Activity Timeline** in the sidebar
2. Browse activities grouped by date
3. Click any activity to see details:
   - Screenshots from that time period
   - Event descriptions
   - Duration and timestamps

**Benefits**:
- Review what you worked on
- Find information from past activities
- Track how you spend time

### 2. AI-Powered Summaries

**What it does**: Uses LLMs to create human-readable activity descriptions

**How it works**:
- Analyzes screenshots and event data
- Generates concise, meaningful titles
- Groups similar events together
- Filters out noise and interruptions

**Example**:
Instead of seeing raw events like:
- `Mouse click at (450, 320)`
- `Keyboard input: "const foo =..."`
- `Window focus: VSCode`

You see:
- `Writing TypeScript code in VSCode`

**Benefits**:
- Easy-to-understand activity history
- No manual note-taking required
- Context-aware descriptions

### 3. Smart Task Recommendations

**What it does**: AI agents analyze your activities and suggest tasks

**How it works**:
1. Agents monitor your activity stream
2. Detect patterns and context (coding, writing, browsing, etc.)
3. Generate relevant task suggestions
4. Prioritize based on importance

**How to use**:
1. Navigate to **Agents** in the sidebar
2. View AI-generated task recommendations
3. Mark tasks as complete
4. See how tasks relate to specific activities

**Example agents**:
- **Code Review Agent**: Suggests code review tasks when you're coding
- **Documentation Agent**: Recommends writing docs after implementing features
- **Research Agent**: Proposes follow-up research based on browsing

**Benefits**:
- Never forget important tasks
- Context-aware reminders
- Learn from your patterns

### 4. Privacy-First Design

**What it does**: Keeps all your data on your device

**How it works**:
- All data stored in local SQLite database
- Screenshots saved to local disk
- LLM calls use your own API key
- No cloud uploads or syncing

**What gets sent to LLM**:
- Screenshots (as base64 data)
- Event summaries (no raw keystrokes)
- Timestamps and window titles

**What never leaves your device**:
- Raw database
- Complete keystroke logs
- Sensitive information

**Benefits**:
- Full control over your data
- Works offline (except LLM calls)
- No subscription or vendor lock-in

### 5. Customizable Capture

**What it does**: Control what and how iDO captures

**Settings you can adjust**:

**Capture Interval**
- How often screenshots are taken
- Default: 1 second
- Range: 0.5 - 5 seconds
- Lower = more detailed, higher = less disk space

**Screen Selection**
- Choose which monitors to capture
- Enable/disable per monitor
- Useful for privacy (exclude personal monitor)

**Image Quality**
- Screenshot compression level
- Default: 85%
- Range: 50% - 100%
- Lower = smaller files, higher = better quality

**Image Optimization**
- Smart screenshot deduplication
- Skips nearly-identical screenshots
- Saves disk space automatically

**How to configure**:
1. Open **Settings** → **Screen Capture**
2. Adjust preferences
3. Click **Save**

### 6. Search and Filter

**What it does**: Find past activities quickly

**Search by**:
- Keywords in activity titles
- Date ranges
- Duration
- Applications used

**How to use**:
1. Go to **Activity Timeline**
2. Use the search bar at the top
3. Apply filters (date, duration, etc.)
4. Click any result to view details

### 7. Multi-Language Support

**What it does**: Use iDO in your preferred language

**Supported languages**:
- English
- 中文 (Chinese)

**How to change**:
1. Open **Settings** → **Preferences**
2. Select **Language**
3. Choose your language
4. UI updates immediately

### 8. Theme Customization

**What it does**: Adjust visual appearance

**Available themes**:
- **Light Mode**: Bright interface
- **Dark Mode**: Easy on the eyes
- **System**: Match OS theme

**How to change**:
1. Open **Settings** → **Appearance**
2. Select theme
3. Changes apply immediately

## Interface Overview

### Dashboard

**What you'll see**:
- System status (Running / Stopped)
- Active LLM model
- Statistics (events captured, activities created)
- Recent activity summary

**Actions**:
- Start/stop activity capture
- View system health
- Quick access to settings

### Activity Timeline

**Layout**:
- Chronological list grouped by date
- Sticky date headers
- Activity cards with:
  - Title
  - Duration
  - Thumbnail screenshot
  - Timestamp

**Interactions**:
- Click activity → View details
- Scroll → Auto-load more
- Search → Filter results

### Activity Details

**What you'll see**:
- Full activity title and description
- All screenshots from that period
- Event timeline
- Related tasks (if any)

**Actions**:
- Navigate between screenshots
- Export activity data
- Generate tasks from this activity

### Agents View

**What you'll see**:
- List of AI-generated tasks
- Task status (pending, completed)
- Priority levels
- Source activities

**Actions**:
- Mark task as complete
- View source activity
- Dismiss tasks

### Settings

**Categories**:
- **LLM Configuration**: API key, model selection
- **Screen Capture**: Monitor selection, intervals
- **Preferences**: Language, theme, notifications
- **Privacy**: Data retention, export options
- **About**: Version info, licenses

## Data Management

### Storage Location

All data is stored locally:
- **macOS**: `~/.config/ido/`
- **Windows**: `%APPDATA%\ido\`
- **Linux**: `~/.config/ido/`

### Data Retention

**Automatic cleanup** (coming soon):
- Screenshots older than 30 days (configurable)
- Completed tasks older than 90 days
- Logs older than 7 days

**Manual cleanup**:
1. **Settings** → **Privacy**
2. Choose what to delete
3. Confirm deletion

### Export Data

**Export options** (coming soon):
- Export activities as JSON
- Export screenshots as ZIP
- Export database backup

## Tips for Best Results

### 1. Configure Permissions Properly

**macOS**: Grant both Accessibility and Screen Recording permissions for full functionality

### 2. Choose the Right LLM Model

- **gpt-4**: Best quality summaries, slower, more expensive
- **gpt-3.5-turbo**: Good quality, faster, cheaper
- **Other models**: Experiment with compatible OpenAI-style APIs

### 3. Adjust Capture Interval

- **Fast work** (coding, design): 1 second intervals
- **General use**: 2-3 second intervals
- **Browsing/reading**: 3-5 second intervals

### 4. Manage Disk Space

- Enable **Image Optimization** to reduce duplicates
- Lower **Image Quality** if disk space is limited
- Disable capture on unused monitors

### 5. Review Activities Regularly

- Check timeline daily to verify accuracy
- Dismiss irrelevant tasks
- Adjust settings based on results

## Privacy Features

### What iDO Respects

✅ **Local storage** - Everything stays on your device
✅ **Your API key** - Use your own LLM provider
✅ **Selective capture** - Choose which monitors to record
✅ **No telemetry** - iDO doesn't phone home
✅ **Open source** - Audit the code yourself

### What to Be Aware Of

⚠️ **Screenshots contain visible content** - Don't capture sensitive screens
⚠️ **LLM sees screenshots** - Sent to OpenAI/your provider
⚠️ **Database is unencrypted** - Store in encrypted volume if needed
⚠️ **Logs may contain info** - Review before sharing

## Limitations

### Current Limitations

- **macOS only** (Windows/Linux coming soon)
- **Single user** (no multi-user accounts)
- **Local only** (no cloud sync)
- **Requires LLM API** (costs apply for API calls)

### Performance Considerations

- **CPU usage**: ~2-5% during capture
- **Memory**: ~200-500 MB RAM
- **Disk**: ~100-500 MB per day (varies by interval and quality)
- **LLM costs**: $0.01-0.10 per hour of activity (varies by model)

## Next Steps

- **[Read FAQ](./faq.md)** - Common questions
- **[Troubleshooting](./troubleshooting.md)** - Fix issues
- **[Installation Guide](./installation.md)** - Re-visit setup

## Need Help?

- 🐛 **Report Issues**: [GitHub Issues](https://github.com/TexasOct/iDO/issues)
- 💬 **Ask Questions**: [GitHub Discussions](https://github.com/TexasOct/iDO/discussions)
- 📖 **Documentation**: [Full Docs](../README.md)

---

**Navigation**: [← Installation](./installation.md) • [User Guide Home](./README.md) • [FAQ →](./faq.md)
