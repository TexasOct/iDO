import { create } from 'zustand'

import type { Live2DStatePayload } from '@/lib/types/live2d'
import { DEFAULT_MODEL_URL, fetchLive2dState, updateLive2dState } from '@/lib/services/live2d'
import { sendModelToLive2d, syncLive2dWindow } from '@/lib/live2d/windowManager'

const DEFAULT_STATE: Live2DStatePayload = {
  settings: {
    enabled: false,
    selectedModelUrl: DEFAULT_MODEL_URL,
    modelDir: '',
    remoteModels: [DEFAULT_MODEL_URL]
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
      syncLive2dWindow(nextState.settings).catch((error) =>
        console.warn('[Live2D] 同步窗口失败', error)
      )
    } catch (error) {
      console.error('[Live2D] 获取配置失败', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : '加载失败'
      })
    }
  },

  setEnabled: async (enabled: boolean) => {
    set({ loading: true, error: null })
    try {
      const nextState = await updateLive2dState({ enabled })
      set({ state: nextState, loading: false, error: null })
      syncLive2dWindow(nextState.settings).catch((error) =>
        console.warn('[Live2D] 同步窗口失败', error)
      )
    } catch (error) {
      console.error('[Live2D] 更新开关失败', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : '更新失败'
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
          console.warn('[Live2D] 同步模型失败', error)
        )
      }
    } catch (error) {
      console.error('[Live2D] 切换模型失败', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : '切换模型失败'
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
          console.warn('[Live2D] 同步模型失败', error)
        )
      }
    } catch (error) {
      console.error('[Live2D] 添加远程模型失败', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : '添加远程模型失败'
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
      syncLive2dWindow(nextState.settings).catch((error) =>
        console.warn('[Live2D] 同步窗口失败', error)
      )
      if (nextState.settings.enabled) {
        sendModelToLive2d(nextState.settings.selectedModelUrl).catch((error) =>
          console.warn('[Live2D] 同步模型失败', error)
        )
      }
    } catch (error) {
      console.error('[Live2D] 删除远程模型失败', error)
      set({
        loading: false,
        error: error instanceof Error ? error.message : '删除远程模型失败'
      })
    }
  }
}))
