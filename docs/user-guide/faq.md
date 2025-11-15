# Frequently Asked Questions (FAQ)

Common questions about iDO and how to use it.

## General Questions

### What is iDO?

iDO is a local-first AI desktop copilot that captures your computer activities, uses LLMs to understand context, and recommends tasks based on what you're doing. Think of it as an AI assistant that watches what you do and helps you stay organized.

### Is iDO free?

iDO itself is free and open source. However, you need to provide your own LLM API key (e.g., OpenAI), which has usage costs. Typical costs are $0.01-0.10 per hour of activity, depending on the model you choose.

### Which platforms are supported?

Currently:
- ✅ **macOS** 13 (Ventura) or later

Coming soon:
- ⏳ **Windows** 10 or later
- ⏳ **Linux** (Ubuntu 20.04+)

### Is my data private?

Yes! iDO is designed with privacy as a priority:
- ✅ All data stored locally on your device
- ✅ No cloud uploads or syncing
- ✅ You control your own LLM API key
- ✅ Open source code (audit it yourself)

The only data that leaves your device is what's sent to your LLM provider (OpenAI or compatible) for analysis.

## Installation & Setup

### Where can I download iDO?

Download the latest version from GitHub Releases:
👉 https://github.com/TexasOct/iDO/releases/latest

### How do I install on macOS?

1. Download the `.dmg` file for your Mac (Intel or Apple Silicon)
2. Open the `.dmg` and drag iDO to Applications
3. Launch iDO from Applications
4. Grant permissions when prompted

See the [Installation Guide](./installation.md) for details.

### Why does macOS block iDO from running?

macOS blocks apps downloaded from the internet as a security measure. To allow iDO:

1. Go to **System Settings** → **Privacy & Security**
2. Find "iDO was blocked from use"
3. Click **Open Anyway**
4. Confirm

### What permissions does iDO need?

On macOS, iDO requires:

**Accessibility** - To monitor keyboard and mouse events
**Screen Recording** - To capture screenshots

You'll be prompted to grant these on first run. See [Installation Guide](./installation.md#1-grant-system-permissions) for details.

### Do I need an OpenAI API key?

Yes, iDO requires an LLM provider to analyze activities. The recommended provider is OpenAI, but any OpenAI-compatible API works (e.g., Azure OpenAI, local LLM servers).

Get an OpenAI API key at: https://platform.openai.com/api-keys

### Which LLM model should I use?

**Recommended**:
- **gpt-4** - Best quality, ~$0.05-0.10 per hour
- **gpt-3.5-turbo** - Good quality, ~$0.01-0.02 per hour

**Tips**:
- Start with gpt-3.5-turbo to save costs
- Upgrade to gpt-4 if summaries aren't accurate enough
- You can change models anytime in Settings

## Usage

### How does iDO track my activities?

iDO uses a three-layer approach:

1. **Perception Layer**: Captures keyboard, mouse, and screenshots every 1-3 seconds
2. **Processing Layer**: Filters noise and uses LLM to create meaningful activity summaries
3. **Consumption Layer**: Displays activities and generates task recommendations

### Will iDO slow down my computer?

iDO is designed to be lightweight:
- CPU: ~2-5% usage during capture
- RAM: ~200-500 MB
- Disk: ~100-500 MB per day

If you notice high resource usage, try:
- Increasing capture interval (Settings → 2-3 seconds)
- Lowering image quality
- Disabling unused monitors

### How much disk space does iDO use?

Storage varies based on your settings:

**Typical usage** (default settings):
- ~100-300 MB per day
- ~3-9 GB per month

**Factors**:
- Capture interval (1s = more screenshots)
- Image quality (85% is default)
- Number of monitors
- Image optimization (reduces duplicates)

### Can I exclude certain screens or apps?

**Monitors**: Yes! Go to Settings → Screen Capture and disable specific monitors.

**Apps**: Not yet, but this feature is planned.

**Workaround**: Stop capture (Dashboard → Stop) when using sensitive apps, then resume.

### What happens to old data?

**Currently**: Data is kept indefinitely until you manually delete it.

**Coming soon**: Automatic cleanup options:
- Delete screenshots older than X days
- Delete completed tasks older than X days
- Keep database but remove old screenshots

### Can I export my data?

**Coming soon**: Export features for activities and screenshots.

**Currently**: You can access the raw database at:
- macOS: `~/.config/ido/ido.db` (SQLite format)

## Troubleshooting

### iDO isn't capturing any activities

**Check**:
1. ✅ Permissions granted (Accessibility + Screen Recording)
2. ✅ At least one monitor enabled in Settings
3. ✅ Capture is running (Dashboard shows "Running")

**Solutions**:
- Restart iDO
- Re-grant permissions (System Settings → Privacy & Security)
- Check logs: `~/.config/ido/logs/app.log`

### LLM connection test fails

**Common causes**:
1. ❌ Invalid API key
2. ❌ No internet connection
3. ❌ API endpoint unreachable

**Solutions**:
- Verify API key is correct (check for extra spaces)
- Test internet connection
- Try a different model
- Check OpenAI service status: https://status.openai.com/

### Screenshots aren't being captured

**Check**:
1. ✅ Screen Recording permission granted
2. ✅ Monitor is enabled in Settings → Screen Capture
3. ✅ Disk has free space

**Solutions**:
- Re-grant Screen Recording permission
- Restart iDO
- Check screenshot folder: `~/.config/ido/screenshots/`

### Activities have generic titles like "Activity 1"

**Cause**: LLM isn't generating proper summaries

**Solutions**:
- Verify LLM connection (Settings → Test Connection)
- Check API key has available credits
- Try a different model (gpt-4 vs gpt-3.5-turbo)
- Review logs for errors

### iDO is using too much CPU/RAM

**Solutions**:
1. Increase capture interval:
   - Settings → Screen Capture → Capture Interval: 2-3 seconds
2. Lower image quality:
   - Settings → Screen Capture → Image Quality: 70%
3. Disable unused monitors:
   - Settings → Screen Capture → Uncheck monitors
4. Enable image optimization:
   - Settings → Screen Capture → Image Optimization: On

### App crashes on startup

**Solutions**:
1. Check logs: `~/.config/ido/logs/app.log`
2. Try resetting settings:
   ```bash
   mv ~/.config/ido/config.toml ~/.config/ido/config.toml.backup
   ```
3. Reinstall iDO
4. Report issue with logs: https://github.com/TexasOct/iDO/issues

## Privacy & Security

### What data does iDO collect?

iDO captures:
- Keyboard and mouse events (timestamps, event types)
- Screenshots (periodic captures)
- Window titles and application names
- Activity timestamps and durations

**Not captured**:
- Raw keystroke content (only event summaries)
- Passwords or secure fields
- Audio or video

### What gets sent to OpenAI?

When processing activities, iDO sends:
- Screenshots (as base64 data)
- Event summaries (e.g., "typing in VSCode")
- Timestamps and window titles

**Not sent**:
- Your raw database
- Complete keystroke logs
- Data from disabled monitors

### Can my company use iDO?

**Things to consider**:
- iDO captures screenshots of everything on your screen
- Data is sent to your LLM provider (OpenAI, etc.)
- Data is stored unencrypted locally

**Recommendations**:
- Check your company's security policy
- Use a company-approved LLM provider
- Consider using Azure OpenAI for enterprise deployments
- Store the database on an encrypted volume
- Don't capture screens with sensitive information

### Is iDO open source?

Yes! iDO is licensed under Apache 2.0.

View the source code: https://github.com/TexasOct/iDO

### How is iDO different from Rewind.ai?

**Similarities**:
- Both capture screen activity
- Both use AI to analyze activities

**Differences**:

| Feature | iDO | Rewind.ai |
|---------|-----|-----------|
| **Source** | Open source | Closed source |
| **Privacy** | Local-only | Cloud option |
| **LLM** | Bring your own | Built-in |
| **Cost** | Free (+ API costs) | Subscription |
| **Platform** | macOS (Linux/Windows coming) | macOS only |

## Features & Roadmap

### Can I sync data across devices?

Not currently. iDO is local-only by design for privacy.

**Possible future options**:
- Self-hosted sync server
- Encrypted cloud backup
- Export/import between devices

### Can iDO integrate with my task manager?

Not yet, but this is planned!

**Planned integrations**:
- Export tasks to Todoist, Things, OmniFocus
- Notion integration
- Calendar integration

### Does iDO work offline?

**Mostly, yes**:
- ✅ Activity capture works offline
- ✅ Browse existing activities offline
- ❌ LLM analysis requires internet (for API calls)

### What features are coming next?

See our roadmap: https://github.com/TexasOct/iDO/issues

**Planned features**:
- Windows and Linux support
- App-specific filtering
- Automatic data retention policies
- Task manager integrations
- Custom agents
- Team/multi-user support

### Can I build custom agents?

**Currently**: Only for developers (requires coding)

**Coming soon**: Visual agent builder for non-developers

See [Developer Documentation](../developers/guides/backend/agents.md) for building custom agents.

## Costs

### How much does iDO cost to run?

**iDO itself**: Free (open source)

**LLM API costs** (varies by usage):
- **Light use** (~2 hours/day): $0.50-2/month
- **Medium use** (~6 hours/day): $2-8/month
- **Heavy use** (~12 hours/day): $5-15/month

**Costs depend on**:
- LLM model (gpt-4 vs gpt-3.5-turbo)
- Capture interval (more screenshots = more API calls)
- Activity complexity

**Tips to reduce costs**:
- Use gpt-3.5-turbo instead of gpt-4
- Increase capture interval to 2-3 seconds
- Disable capture when not needed

### Can I use a local LLM instead?

Yes! iDO works with any OpenAI-compatible API endpoint.

**Options**:
- LM Studio (local)
- Ollama (local)
- LocalAI (local)
- Azure OpenAI (cloud)
- Other OpenAI-compatible services

**Note**: Quality varies by model. For best results, use models with vision capabilities.

## Still Have Questions?

- 💬 **Ask in Discussions**: [GitHub Discussions](https://github.com/TexasOct/iDO/discussions)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/TexasOct/iDO/issues)
- 📖 **Read Docs**: [Full Documentation](../README.md)

---

**Navigation**: [← Features](./features.md) • [User Guide Home](./README.md) • [Troubleshooting →](./troubleshooting.md)
