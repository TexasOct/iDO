# System Tray Implementation

## Overview

The system tray is implemented in **JavaScript/TypeScript** using Tauri's `@tauri-apps/api/tray` API. This approach is easier to understand and maintain compared to Rust implementation, and allows for seamless i18n integration.

## Architecture

### Files

- **`src/hooks/useTray.ts`**: Main tray hook that creates and manages the tray icon
- **`src/views/App.tsx`**: Initializes the tray when the app starts
- **`src/locales/en.ts`** & **`src/locales/zh-CN.ts`**: i18n translations for menu items

### Key Features

1. **i18n Support**: All menu items are translated using `react-i18next`
2. **Dynamic Updates**: Tray menu automatically updates when language changes
3. **Navigation**: Menu items can navigate to different app pages
4. **Window Management**: Show/hide/focus window functionality

## Menu Structure

```
├── Show Window
├── Hide Window
├── ──────────────
├── Dashboard
├── Activity
├── Chat
├── Agents
├── Settings
├── ──────────────
├── About iDO
├── ──────────────
└── Quit
```

## Implementation Details

### Creating the Tray

```typescript
const tray = await TrayIcon.new({
  menu,
  menuOnLeftClick: false, // Right-click only
  tooltip: 'iDO - AI Activity Monitor',
  action: async (event) => {
    // Handle left-click on icon
  }
})
```

### Menu Items with Actions

```typescript
const dashboardItem = await MenuItem.new({
  id: 'dashboard',
  text: t('tray.dashboard'),
  action: async () => {
    const window = getCurrentWindow()
    await window.unminimize()
    await window.show()
    await window.setFocus()
    navigate('/dashboard')
  }
})
```

### Language Updates

The tray automatically reinitializes when the language changes:

```typescript
useEffect(() => {
  // ... tray initialization
}, [t, navigate, currentLanguage])
```

## i18n Keys

Add translations in `src/locales/en.ts` and `src/locales/zh-CN.ts`:

```typescript
tray: {
  show: 'Show Window',
  hide: 'Hide Window',
  dashboard: 'Dashboard',
  activity: 'Activity',
  chat: 'Chat',
  agents: 'Agents',
  settings: 'Settings',
  quit: 'Quit',
  about: 'About iDO',
  version: 'Version {{version}}'
}
```

## Testing

### Development Mode

```bash
pnpm tauri dev
```

**Test Cases:**
1. ✅ Tray icon appears in system tray
2. ✅ Right-click shows menu
3. ✅ Left-click shows/focuses window
4. ✅ Menu items navigate to correct pages
5. ✅ Show/Hide works correctly
6. ✅ Quit exits the application
7. ✅ Language switching updates menu labels

### Language Switching Test

1. Launch app in English
2. Check tray menu shows English labels
3. Switch to Chinese in Settings
4. Check tray menu shows Chinese labels

### Navigation Test

1. Hide or minimize the app window
2. Right-click tray icon
3. Click "Dashboard" (or any navigation item)
4. Window should show and navigate to that page

## Platform-Specific Notes

### macOS
- Tray icon uses the app's default icon
- Menu appears on right-click by default
- Left-click on icon shows/focuses window

### Windows
- Tray icon appears in system notification area
- Right-click shows menu
- Left-click shows/focuses window

### Linux
- Support depends on desktop environment
- Most modern DEs support tray icons
- Behavior similar to Windows

## Troubleshooting

### Tray icon not showing
- Ensure `tray-icon` feature is enabled in `src-tauri/Cargo.toml`
- Check console for initialization errors
- Verify app icon is properly configured

### Menu not updating on language change
- The tray is recreated when language changes via the `useEffect` dependency array
- Check that `i18n.language` is properly tracked

### Navigation not working
- Ensure `react-router` is properly set up
- Check that route paths match the ones in menu items
- Verify window focus/show calls are succeeding

## Future Enhancements

Possible improvements:
- [ ] Badge/notification count on tray icon
- [ ] Dynamic menu items based on app state
- [ ] Context-sensitive actions
- [ ] System tray icon changes based on app status
- [ ] Version info in about menu item

## References

- [Tauri System Tray Documentation](https://v2.tauri.app/learn/system-tray/)
- [Tauri TrayIcon API](https://v2.tauri.app/reference/javascript/api/namespacetrayi/)
- [Tauri Menu API](https://v2.tauri.app/reference/javascript/api/namespacemenu/)
