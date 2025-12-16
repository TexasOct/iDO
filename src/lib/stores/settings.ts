import { create } from 'zustand'
import type { AppSettings, DatabaseSettings, ScreenshotSettings } from '@/lib/types/settings'
import * as apiClient from '@/lib/client/apiClient'

interface SettingsState {
  settings: AppSettings
  loading: boolean
  error: string | null

  // Actions
  fetchSettings: () => Promise<void>
  updateDatabaseSettings: (database: Partial<DatabaseSettings>) => Promise<void>
  updateScreenshotSettings: (screenshot: Partial<ScreenshotSettings>) => Promise<void>
  updateTheme: (theme: 'light' | 'dark' | 'system') => void
  updateLanguage: (language: 'zh-CN' | 'en-US') => Promise<void>
}

const defaultSettings: AppSettings = {
  database: {
    path: ''
  },
  screenshot: {
    savePath: ''
  },
  theme: 'system',
  language: 'zh-CN'
}

export const useSettingsStore = create<SettingsState>()((set, get) => ({
  settings: defaultSettings,
  loading: false,
  error: null,

  fetchSettings: async () => {
    set({ loading: true, error: null })
    try {
      const response = await apiClient.getSettingsInfo(undefined)
      if (response && response.data) {
        const data = response.data as any
        const { database, screenshot } = data
        if (database || screenshot) {
          set((state) => ({
            settings: {
              ...state.settings,
              ...(database && { database: { path: database.path } }),
              ...(screenshot && { screenshot: { savePath: screenshot.savePath } })
            },
            loading: false,
            error: null
          }))
        } else {
          set({ loading: false, error: null })
        }
      } else {
        set({ loading: false, error: null })
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  updateDatabaseSettings: async (database) => {
    set({ loading: true, error: null })
    try {
      const state = get()
      const fullDatabase = { ...(state.settings.database || {}), ...database }
      await apiClient.updateSettings({
        databasePath: fullDatabase.path || null
      } as any)
      set({
        settings: {
          ...state.settings,
          database: fullDatabase as DatabaseSettings
        },
        loading: false,
        error: null
      })
    } catch (error) {
      console.error('Failed to update database settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  updateScreenshotSettings: async (screenshot) => {
    set({ loading: true, error: null })
    try {
      const state = get()
      const fullScreenshot = { ...(state.settings.screenshot || {}), ...screenshot }
      await apiClient.updateSettings({
        screenshotSavePath: fullScreenshot.savePath || null
      } as any)
      set({
        settings: {
          ...state.settings,
          screenshot: fullScreenshot as ScreenshotSettings
        },
        loading: false,
        error: null
      })
    } catch (error) {
      console.error('Failed to update screenshot settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  updateTheme: (theme) =>
    set((state) => ({
      settings: { ...state.settings, theme }
    })),

  updateLanguage: async (language) => {
    // Update frontend state immediately for better UX
    set((state) => ({
      settings: { ...state.settings, language }
    }))

    try {
      // Map frontend language codes to backend language codes
      const backendLanguage = language === 'zh-CN' ? 'zh' : 'en'
      await apiClient.updateSettings({
        language: backendLanguage
      } as any)
      console.log(`✓ Backend language updated to: ${backendLanguage}`)
    } catch (error) {
      console.error('Failed to update backend language:', error)
      // Rollback frontend state on error
      const currentState = get()
      set((state) => ({
        settings: { ...state.settings, language: currentState.settings.language }
      }))
    }
  }
}))
