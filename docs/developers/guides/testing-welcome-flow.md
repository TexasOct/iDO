# Testing the Welcome Flow (Initial Setup)

This guide explains how to test the welcome/initial setup flow during development.

## Overview

The Initial Setup Flow (`InitialSetupFlow.tsx`) is a multi-step onboarding experience that guides new users through:
1. **Welcome** - Introduction to iDO
2. **Model Setup** - Configure LLM model
3. **Permissions** - Grant system permissions
4. **Complete** - Finish setup

The setup state is persisted in `localStorage` under the key `ido-initial-setup`.

## Quick Testing Methods

### Method 1: Keyboard Shortcuts (Fastest) ⚡

Development keyboard shortcuts are automatically available when running in dev mode.

**Available Shortcuts:**

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Cmd/Ctrl + Shift + R` | Reset to Welcome | Resets entire flow to step 1 |
| `Cmd/Ctrl + Shift + O` | Reopen Current | Shows overlay at current step |
| `Cmd/Ctrl + Shift + S` | Show State | Logs current setup state to console |
| `Cmd/Ctrl + Shift + 1` | Jump to Welcome | Go directly to welcome screen |
| `Cmd/Ctrl + Shift + 2` | Jump to Model | Go directly to model setup |
| `Cmd/Ctrl + Shift + 3` | Jump to Permissions | Go directly to permissions |
| `Cmd/Ctrl + Shift + 4` | Jump to Complete | Go directly to completion |

**Usage:**
1. Run `pnpm dev` or `pnpm tauri dev`
2. Press any shortcut (no need to navigate anywhere)
3. Toast notifications confirm the action
4. Check browser console for available shortcuts list

**Pro Tip:** Use `Cmd/Ctrl + Shift + [1-4]` to quickly jump between steps during development!

### Method 2: Developer Tools Panel (Most Visual)

A developer tools panel is available in **Settings** (only visible in development mode).

**Steps:**
1. Run `pnpm dev` or `pnpm tauri dev`
2. Navigate to **Settings** page
3. Scroll to the bottom to find **Developer Tools**
4. Click to expand the panel

**Available Actions:**

- **Reset to Welcome**: Resets the entire flow to step 1 (welcome screen)
  - Sets `isActive: true`
  - Sets `hasAcknowledged: false`
  - Sets `currentStep: 'welcome'`
  - Useful for testing the complete flow from scratch

- **Reopen Current Step**: Shows the overlay at the current step without resetting progress
  - Sets `isActive: true` (without changing `currentStep` or `hasAcknowledged`)
  - Useful for testing a specific step you're working on

- **Clear All Local Storage**: Nuclear option - clears ALL browser data
  - Removes all persisted state (settings, models, setup progress, etc.)
  - Requires page reload
  - Use with caution!

**Current State Display:**
The panel shows the current setup state:
- Status: Active/Inactive
- Acknowledged: Yes/No
- Current Step: welcome/model/permissions/complete

### Method 3: Browser DevTools (Manual)

If you prefer direct control, use browser console:

```javascript
// Reset to welcome screen
localStorage.setItem('ido-initial-setup', JSON.stringify({
  state: {
    isActive: true,
    hasAcknowledged: false,
    currentStep: 'welcome'
  },
  version: 0
}))
window.location.reload()

// Skip to a specific step (e.g., permissions)
localStorage.setItem('ido-initial-setup', JSON.stringify({
  state: {
    isActive: true,
    hasAcknowledged: false,
    currentStep: 'permissions'
  },
  version: 0
}))
window.location.reload()

// Hide the overlay (simulate completed setup)
localStorage.setItem('ido-initial-setup', JSON.stringify({
  state: {
    isActive: false,
    hasAcknowledged: true,
    currentStep: 'complete'
  },
  version: 0
}))
window.location.reload()

// Completely remove setup state
localStorage.removeItem('ido-initial-setup')
window.location.reload()
```

### Method 4: Zustand Store API (Runtime)

Use the store actions directly in your code or console:

```javascript
// Access the store
const { reset, reopen, goToStep, skipForNow } = window.useSetupStore?.getState() || {}

// Reset to welcome
reset()

// Reopen current step
reopen()

// Jump to a specific step
goToStep('permissions')

// Skip and hide
skipForNow()
```

## Testing Scenarios

### Scenario 1: First-Time User Experience
**Goal:** Test the complete onboarding flow as a new user would see it.

1. Use Developer Tools → "Reset to Welcome"
2. Go through each step:
   - Welcome screen → click "Start"
   - Model setup → create/configure a model → click "Continue"
   - Permissions → grant permissions → auto-advances
   - Completion → click "Launch iDO"
3. Verify setup is hidden after completion

### Scenario 2: Testing Individual Steps
**Goal:** Test changes to a specific step without going through the whole flow.

1. Use Developer Tools → "Reset to Welcome"
2. Use browser console to jump to the step you want:
   ```javascript
   window.useSetupStore.getState().goToStep('model')
   ```
3. Test your changes
4. Repeat as needed

### Scenario 3: Testing Permissions Auto-Advance
**Goal:** Verify that the permissions step auto-advances when all permissions are granted.

1. Jump to permissions step:
   ```javascript
   window.useSetupStore.getState().goToStep('permissions')
   ```
2. Grant all required permissions through system settings
3. Click "Recheck" button
4. Verify it auto-advances to completion screen within ~800ms

### Scenario 4: Testing Skip Behavior
**Goal:** Test that users can skip the setup.

1. Reset to welcome
2. Click "Skip for Now" on welcome screen
3. Verify overlay is hidden
4. Verify `hasAcknowledged` is set to `true`

### Scenario 5: Testing Restart Scenario
**Goal:** Test the flow when permissions require an app restart.

1. Jump to permissions step
2. Trigger a restart scenario (platform-dependent)
3. Verify `pendingRestart` flag is set
4. Verify setup doesn't auto-advance until restart completes

## Setup Store State Reference

```typescript
interface SetupState {
  isActive: boolean        // Whether overlay is showing
  hasAcknowledged: boolean // Whether user finished/skipped setup
  currentStep: SetupStep   // Current step: 'welcome' | 'model' | 'permissions' | 'complete'
}
```

**State Logic:**
- Overlay shows when: `isActive === true && hasAcknowledged === false`
- Overlay hides when: `isActive === false || hasAcknowledged === true`

## Common Issues & Solutions

### Issue: Setup keeps reappearing after completion
**Cause:** `hasAcknowledged` is not being set to `true`
**Solution:** Ensure `completeAndAcknowledge()` is called when user clicks final button

### Issue: Can't test welcome screen after viewing it once
**Cause:** State is persisted in localStorage
**Solution:** Use Developer Tools → "Reset to Welcome"

### Issue: Changes to setup flow not reflecting
**Cause:** HMR may not update the overlay component
**Solution:** Hard reload (`Cmd+Shift+R` or `Ctrl+Shift+R`)

### Issue: Permissions step stuck, won't advance
**Cause:** Auto-advance logic depends on `permissionsData.allGranted`
**Solution:** Check `usePermissionsStore` state and ensure permissions are actually granted

## Tips for Development

1. **Keep Developer Tools open** while working on setup flow
2. **Use "Reopen Current Step"** for quick iterations on a single step
3. **Check localStorage** if state seems inconsistent
4. **Test with real permissions** on macOS to verify auto-advance logic
5. **Test skip flow** to ensure users can exit at any point

## Integration with App.tsx

The setup flow is conditionally rendered in `App.tsx`:

```typescript
{(!isSetupActive || hasAcknowledged) && <PermissionsGuide />}
```

This hides the global `PermissionsGuide` while setup is active to avoid UI conflicts.

## Related Files

- `src/components/setup/InitialSetupFlow.tsx` - Main setup component
- `src/lib/stores/setup.ts` - Setup state management
- `src/views/App.tsx` - Integration point
- `src/components/settings/DeveloperSettings.tsx` - Testing utilities

## Further Reading

- [Zustand Persist Middleware](https://docs.pmnd.rs/zustand/integrations/persisting-store-data)
- [Project Structure](../../CLAUDE.md#project-structure)
