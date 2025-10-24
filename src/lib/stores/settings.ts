import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { AppSettings, LLMSettings, DatabaseSettings, ScreenshotSettings } from '@/lib/types/settings'
import * as apiClient from '@/lib/client/apiClient'

interface SettingsState {
  settings: AppSettings
  loading: boolean
  error: string | null

  // Actions
  fetchSettings: () => Promise<void>
  updateLLMSettings: (llm: Partial<LLMSettings>) => Promise<void>
  updateDatabaseSettings: (database: Partial<DatabaseSettings>) => Promise<void>
  updateScreenshotSettings: (screenshot: Partial<ScreenshotSettings>) => Promise<void>
  updateAllSettings: (settings: Partial<AppSettings>) => Promise<void>
  updateTheme: (theme: 'light' | 'dark' | 'system') => void
  updateLanguage: (language: 'zh-CN' | 'en-US') => void
}

const defaultSettings: AppSettings = {
  llm: {
    provider: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    apiKey: '',
    model: 'gpt-4'
  },
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
            const { llm, database, screenshot } = data
            if (llm || database || screenshot) {
              set((state) => ({
                settings: {
                  ...state.settings,
                  ...(llm && { llm: { ...state.settings.llm, ...llm } }),
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

      updateLLMSettings: async (llm) => {
        set({ loading: true, error: null })
        try {
          const state = _get()
          const fullLLM = { ...state.settings.llm, ...llm }
          await apiClient.updateSettings({
            llm: {
              provider: fullLLM.provider,
              apiKey: fullLLM.apiKey,
              model: fullLLM.model,
              baseUrl: fullLLM.baseUrl
            }
          } as any)
          set({
            settings: {
              ...state.settings,
              llm: fullLLM
            },
            loading: false,
            error: null
          })
        } catch (error) {
          console.error('Failed to update LLM settings:', error)
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

      updateAllSettings: async (newSettings) => {
        set({ loading: true, error: null })
        try {
          const state = _get()
          const fullLLM = newSettings.llm ? { ...state.settings.llm, ...newSettings.llm } : state.settings.llm
          const fullDatabase = newSettings.database
            ? { ...(state.settings.database || {}), ...newSettings.database }
            : state.settings.database
          const fullScreenshot = newSettings.screenshot
            ? { ...(state.settings.screenshot || {}), ...newSettings.screenshot }
            : state.settings.screenshot

          const updatePayload: any = {}
          if (newSettings.llm) {
            updatePayload.llm = {
              provider: fullLLM.provider,
              apiKey: fullLLM.apiKey,
              model: fullLLM.model,
              baseUrl: fullLLM.baseUrl
            }
          }
          if (newSettings.database) {
            updatePayload.databasePath = fullDatabase?.path || null
          }
          if (newSettings.screenshot) {
            updatePayload.screenshotSavePath = fullScreenshot?.savePath || null
          }

          await apiClient.updateSettings(updatePayload)
          set({
            settings: {
              ...state.settings,
              ...(newSettings.llm && { llm: fullLLM }),
              ...(newSettings.database && { database: fullDatabase }),
              ...(newSettings.screenshot && { screenshot: fullScreenshot })
            },
            loading: false,
            error: null
          })
        } catch (error) {
          console.error('Failed to update all settings:', error)
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
      name: 'rewind-settings'
    }
  )
)
