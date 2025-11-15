# Installation Guide

This guide will help you download and install iDO on your computer.

## System Requirements

### Supported Platforms

- **macOS**: 13 (Ventura) or later
- **Windows**: 10 or later (Coming soon)
- **Linux**: Ubuntu 20.04+ or equivalent (Coming soon)

### Minimum Hardware

- **CPU**: 64-bit processor
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk Space**: 500 MB for application, plus space for activity data
- **Display**: 1280x720 minimum resolution

## Download iDO

### Latest Release

Download the latest version from GitHub:

👉 **[Download iDO Latest Release](https://github.com/TexasOct/iDO/releases/latest)**

### Choose Your Platform

#### macOS
- Download `iDO_x.x.x_aarch64.dmg` (Apple Silicon - M1/M2/M3)
- Download `iDO_x.x.x_x64.dmg` (Intel Mac)

#### Windows (Coming Soon)
- `iDO_x.x.x_x64_en-US.msi` - Windows installer

#### Linux (Coming Soon)
- `ido_x.x.x_amd64.deb` - Debian/Ubuntu
- `ido-x.x.x-1.x86_64.rpm` - Fedora/RHEL
- `ido_x.x.x_amd64.AppImage` - Universal Linux

## Installation Steps

### macOS

1. **Download** the appropriate `.dmg` file for your Mac
2. **Open** the downloaded `.dmg` file
3. **Drag** iDO to your Applications folder
4. **Launch** iDO from Applications

**First Launch Note**: macOS may show a security warning since the app is downloaded from the internet.

**To allow iDO to run**:
1. Go to **System Settings** → **Privacy & Security**
2. Scroll down to find "iDO was blocked from use"
3. Click **Open Anyway**
4. Confirm by clicking **Open**

### Windows (Coming Soon)

1. **Download** the `.msi` installer
2. **Double-click** the installer
3. **Follow** the installation wizard
4. **Launch** iDO from the Start Menu

### Linux (Coming Soon)

#### Debian/Ubuntu (.deb)
```bash
sudo dpkg -i ido_x.x.x_amd64.deb
sudo apt-get install -f  # Install dependencies
```

#### Fedora/RHEL (.rpm)
```bash
sudo rpm -i ido-x.x.x-1.x86_64.rpm
```

#### AppImage (Universal)
```bash
chmod +x ido_x.x.x_amd64.AppImage
./ido_x.x.x_amd64.AppImage
```

## First Run Setup

When you first launch iDO, you'll need to complete some setup steps:

### 1. Grant System Permissions

#### macOS Permissions

iDO requires the following permissions:

**Accessibility Permission** (Required)
- Allows iDO to monitor keyboard and mouse events
- Go to **System Settings** → **Privacy & Security** → **Accessibility**
- Enable iDO in the list

**Screen Recording Permission** (Required)
- Allows iDO to capture screenshots
- Go to **System Settings** → **Privacy & Security** → **Screen Recording**
- Enable iDO in the list

iDO will guide you through granting these permissions on first run.

### 2. Configure LLM Provider

iDO uses an LLM (Large Language Model) to analyze your activities:

1. **Open Settings** → **LLM Configuration**
2. **Choose Provider**: OpenAI (recommended) or compatible API
3. **Enter API Key**: Your OpenAI API key
   - Get one at https://platform.openai.com/api-keys
4. **Select Model**: 
   - `gpt-4` - Most capable (recommended)
   - `gpt-3.5-turbo` - Faster and cheaper
5. **Test Connection**: Click to verify it works

**Privacy Note**: Your API key is stored locally and used only to make LLM requests on your behalf. iDO does not send data to any iDO servers.

### 3. Configure Screen Capture (Optional)

Choose which monitors to capture:

1. **Open Settings** → **Screen Capture**
2. **View Monitors**: See all detected displays
3. **Toggle On/Off**: Enable/disable specific monitors
4. **Save**: Apply your preferences

By default, only the primary monitor is enabled.

### 4. Adjust Preferences (Optional)

Fine-tune iDO to your liking:

- **Capture Interval**: How often to take screenshots (default: 1 second)
- **Image Quality**: Balance quality vs disk space (default: 85%)
- **Language**: English or 中文 (Chinese)
- **Theme**: Light or Dark mode

## Verify Installation

To verify iDO is working correctly:

1. **Check Dashboard**: You should see system status as "Running"
2. **Use Your Computer**: Browse, type, etc. for 1-2 minutes
3. **View Timeline**: Navigate to Activity Timeline
4. **See Activities**: You should see captured activities with screenshots

## Data Storage

iDO stores all data locally on your device:

- **macOS**: `~/.config/ido/`
- **Windows**: `%APPDATA%\ido\`
- **Linux**: `~/.config/ido/`

This directory contains:
- `ido.db` - SQLite database (activities, events, settings)
- `screenshots/` - Captured screenshots
- `logs/` - Application logs

## Uninstallation

### macOS
1. **Quit** iDO
2. **Drag** iDO from Applications to Trash
3. **Remove data** (optional): Delete `~/.config/ido/`

### Windows (Coming Soon)
1. **Control Panel** → **Programs** → **Uninstall a program**
2. Select iDO and click **Uninstall**
3. **Remove data** (optional): Delete `%APPDATA%\ido\`

### Linux (Coming Soon)
```bash
# Debian/Ubuntu
sudo apt remove ido

# Fedora/RHEL
sudo rpm -e ido

# Remove data (optional)
rm -rf ~/.config/ido/
```

## Troubleshooting

### App Won't Launch

**macOS**: Check System Settings → Privacy & Security for blocked apps

**Solution**: Click "Open Anyway" as described above

### No Activities Being Captured

**Issue**: Dashboard shows 0 events

**Solutions**:
1. Verify permissions are granted (Accessibility + Screen Recording)
2. Check that at least one monitor is enabled in Settings
3. Restart the app

### LLM Connection Failed

**Issue**: Test connection fails

**Solutions**:
1. Verify your API key is correct
2. Check your internet connection
3. Try a different model (e.g., switch from gpt-4 to gpt-3.5-turbo)

### High CPU/Memory Usage

**Issue**: iDO is using too many resources

**Solutions**:
1. Increase capture interval (Settings → 2-3 seconds instead of 1)
2. Lower image quality (Settings → 70% instead of 85%)
3. Disable unused monitors

For more troubleshooting help, see the [Troubleshooting Guide](./troubleshooting.md).

## Next Steps

- **[Learn about Features](./features.md)** - Discover what iDO can do
- **[Read FAQ](./faq.md)** - Common questions answered
- **[Get Help](./troubleshooting.md)** - Solve common issues

## Need Help?

- 🐛 **Report Issues**: [GitHub Issues](https://github.com/TexasOct/iDO/issues)
- 💬 **Ask Questions**: [GitHub Discussions](https://github.com/TexasOct/iDO/discussions)
- 📖 **Documentation**: [Full Docs](../README.md)

---

**Navigation**: [← Back to User Guide](./README.md) • [Next: Features →](./features.md)
