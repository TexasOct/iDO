import { pyInvoke } from 'tauri-plugin-pytauri-api'

// Lightweight client wrappers for screen-related commands
// Kept separate from generated apiClient.ts to avoid touching generated code.

export async function getMonitors() {
  return await pyInvoke('get_monitors', undefined)
}

export async function getScreenSettings() {
  return await pyInvoke('get_screen_settings', undefined)
}

export async function updateScreenSettings(body: { screens: any[] }) {
  return await pyInvoke('update_screen_settings', body as any)
}

export async function captureAllPreviews() {
  return await pyInvoke('capture_all_previews', undefined)
}

export async function getPerceptionSettings() {
  return await pyInvoke('get_perception_settings', undefined)
}

export async function updatePerceptionSettings(body: { keyboard_enabled?: boolean; mouse_enabled?: boolean }) {
  return await pyInvoke('update_perception_settings', body as any)
}

export async function startMonitorsAutoRefresh(body: { interval_seconds?: number } = {}) {
  return await pyInvoke('start_monitors_auto_refresh', body as any)
}

export async function stopMonitorsAutoRefresh() {
  return await pyInvoke('stop_monitors_auto_refresh', undefined)
}

export async function getMonitorsAutoRefreshStatus() {
  return await pyInvoke('get_monitors_auto_refresh_status', undefined)
}

