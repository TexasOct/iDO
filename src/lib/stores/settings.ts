import { create } from 'zustand'
import { persist } from 'zustand/middleware'
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
  updateLanguage: (language: 'zh-CN' | 'en-US') => void
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

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, _get) => ({
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
          const state = _get()
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
          const state = _get()
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

      updateLanguage: (language) =>
        set((state) => ({
          settings: { ...state.settings, language }
        }))
    }),
    {
      name: 'ido-settings'
    }
  )
)
