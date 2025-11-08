import { emitTo } from '@tauri-apps/api/event'
import { PhysicalPosition, getCurrentWindow } from '@tauri-apps/api/window'
import { WebviewWindow } from '@tauri-apps/api/webviewWindow'

import type { Live2DSettings } from '@/lib/types/live2d'
import { isTauri } from '@/lib/utils/tauri'

const WINDOW_LABEL = 'rewind-live2d'
let initializing = false

const createLive2dWindow = async (modelUrl: string) => {
  // Use different URL formats for dev vs production
  // In dev: use dev server absolute path
  // In production: PyTauri uses tauri:// protocol to serve bundled assets
  const url = import.meta.env.DEV ? '/live2d.html' : 'tauri://localhost/live2d.html'

  const win = new WebviewWindow(WINDOW_LABEL, {
    url,
    width: 320,
    height: 460,
    minWidth: 50,
    minHeight: 50,
    transparent: true,
    decorations: false,
    shadow: false,
    alwaysOnTop: true,
    resizable: true,
    focus: true,
    skipTaskbar: true
  })

  try {
    const mainWindow = getCurrentWindow()
    const current = await mainWindow.outerPosition()
    const size = await mainWindow.outerSize()
    const x = current.x + size.width - 360
    const y = current.y + size.height - 520
    await win.setPosition(new PhysicalPosition(x, y))
  } catch (error) {
    console.warn('[Live2D] Failed to position window', error)
  }

  win.once('tauri://created', async () => {
    if (modelUrl) {
      await emitTo(WINDOW_LABEL, 'live2d-load-model', { modelUrl })
    }
  })

  win.once('tauri://error', (event) => {
    console.error('[Live2D] Window error', event)
  })

  return win
}

export const ensureLive2dWindow = async (modelUrl: string) => {
  if (!isTauri()) return null

  const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
  if (existing) {
    try {
      await existing.show()
      await existing.setFocus()
      if (modelUrl) {
        await emitTo(WINDOW_LABEL, 'live2d-load-model', { modelUrl })
      }
    } catch (error) {
      console.warn('[Live2D] Unable to focus live2d window', error)
    }
    return existing
  }

  if (initializing) {
    return await WebviewWindow.getByLabel(WINDOW_LABEL)
  }

  initializing = true
  try {
    const win = await createLive2dWindow(modelUrl)
    return win
  } finally {
    initializing = false
  }
}

export const closeLive2dWindow = async () => {
  if (!isTauri()) return
  const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
  if (existing) {
    try {
      await existing.close()
    } catch (error) {
      console.warn('[Live2D] Failed to close window', error)
    }
  }
}

export const syncLive2dWindow = async (settings: Live2DSettings) => {
  if (!isTauri()) return
  if (settings.enabled) {
    await ensureLive2dWindow(settings.selectedModelUrl)
  } else {
    await closeLive2dWindow()
  }
}

export const sendModelToLive2d = async (modelUrl: string) => {
  if (!isTauri()) return
  await emitTo(WINDOW_LABEL, 'live2d-load-model', { modelUrl })
}

export const sendLive2dSettingsUpdate = async (settings: Pick<Live2DSettings, 'notificationDuration'>) => {
  if (!isTauri()) return
  await emitTo(WINDOW_LABEL, 'live2d-settings-updated', settings)
}
