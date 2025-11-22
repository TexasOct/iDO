import { create } from 'zustand'

import type { Live2DStatePayload } from '@/lib/types/live2d'
import { DEFAULT_MODEL_URL, fetchLive2dState, updateLive2dState } from '@/lib/services/live2d'
import { sendLive2dSettingsUpdate, sendModelToLive2d, syncLive2dWindow } from '@/lib/live2d/windowManager'

const DEFAULT_STATE: Live2DStatePayload = {
  settings: {
    enabled: false,
    selectedModelUrl: DEFAULT_MODEL_URL,
    modelDir: '',
    remoteModels: [DEFAULT_MODEL_URL],
    notificationDuration: 5000 // Default 5 seconds
  },
  models: [
    {
      url: DEFAULT_MODEL_URL,
      type: 'remote',
      name: 'Default Model'
    }
  ]
}

interface Live2DStoreState {
  state: Live2DStatePayload
  loading: boolean
  error: string | null

  fetch: () => Promise<void>
  setEnabled: (enabled: boolean) => Promise<void>
  selectModel: (url: string) => Promise<void>
  addRemoteModel: (url: string) => Promise<void>
  removeRemoteModel: (url: string) => Promise<void>
  setNotificationDuration: (duration: number) => Promise<void>
}

export const useLive2dStore = create<Live2DStoreState>((set, get) => ({
  state: DEFAULT_STATE,
  loading: false,
  error: null,

  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const nextState = await fetchLive2dState()
      set({ state: nextState, loading: false, error: null })
      syncLive2dWindow(nextState.settings).catch((error) => console.warn('[Live2D] Failed to sync window', error))
    } catch (error) {
      console.error('[Live2D] Failed to load configuration', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Load failed'
      })
    }
  },

  setEnabled: async (enabled: boolean) => {
    set({ loading: true, error: null })
    try {
      const nextState = await updateLive2dState({ enabled })
      set({ state: nextState, loading: false, error: null })
      syncLive2dWindow(nextState.settings).catch((error) => console.warn('[Live2D] Failed to sync window', error))
    } catch (error) {
      console.error('[Live2D] Failed to update enabled state', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Update failed'
      })
    }
  },

  selectModel: async (url: string) => {
    if (!url) return
    set({ loading: true, error: null })
    try {
      const nextState = await updateLive2dState({ selectedModelUrl: url })
      set({ state: nextState, loading: false, error: null })
      if (nextState.settings.enabled) {
        sendModelToLive2d(nextState.settings.selectedModelUrl).catch((error) =>
          console.warn('[Live2D] Failed to sync model', error)
        )
      }
    } catch (error) {
      console.error('[Live2D] Failed to switch model', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Model switch failed'
      })
    }
  },

  addRemoteModel: async (url: string) => {
    const trimmed = url.trim()
    if (!trimmed) return
    const current = get().state.settings.remoteModels
    if (current.includes(trimmed)) return

    set({ loading: true, error: null })
    try {
      const nextState = await updateLive2dState({
        remoteModels: [...current, trimmed],
        selectedModelUrl: trimmed
      })
      set({ state: nextState, loading: false, error: null })
      if (nextState.settings.enabled) {
        sendModelToLive2d(nextState.settings.selectedModelUrl).catch((error) =>
          console.warn('[Live2D] Failed to sync model', error)
        )
      }
    } catch (error) {
      console.error('[Live2D] Failed to add remote model', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to add remote model'
      })
    }
  },

  removeRemoteModel: async (url: string) => {
    const currentList = get().state.settings.remoteModels
    const nextList = currentList.filter((item) => item !== url)
    set({ loading: true, error: null })
    try {
      const nextState = await updateLive2dState({
        remoteModels: nextList.length > 0 ? nextList : [DEFAULT_MODEL_URL],
        selectedModelUrl:
          nextList.length > 0
            ? nextList.includes(get().state.settings.selectedModelUrl)
              ? get().state.settings.selectedModelUrl
              : nextList[0]
            : DEFAULT_MODEL_URL
      })
      set({ state: nextState, loading: false, error: null })
      syncLive2dWindow(nextState.settings).catch((error) => console.warn('[Live2D] Failed to sync window', error))
      if (nextState.settings.enabled) {
        sendModelToLive2d(nextState.settings.selectedModelUrl).catch((error) =>
          console.warn('[Live2D] Failed to sync model', error)
        )
      }
    } catch (error) {
      console.error('[Live2D] Failed to delete remote model', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to delete remote model'
      })
    }
  },

  setNotificationDuration: async (duration: number) => {
    const clampedDuration = Math.max(1000, Math.min(30000, duration))
    set({ loading: true, error: null })
    try {
      const nextState = await updateLive2dState({ notificationDuration: clampedDuration })
      set({ state: nextState, loading: false, error: null })
      syncLive2dWindow(nextState.settings).catch((error) => console.warn('[Live2D] Failed to sync window', error))
      sendLive2dSettingsUpdate({ notificationDuration: nextState.settings.notificationDuration }).catch((error) =>
        console.warn('[Live2D] Failed to update notification settings', error)
      )
    } catch (error) {
      console.error('[Live2D] Failed to update notification duration', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to update notification duration'
      })
    }
  }
}))
