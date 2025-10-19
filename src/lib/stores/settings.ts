import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { AppSettings, LLMSettings } from '@/lib/types/settings'

interface SettingsState {
  settings: AppSettings
  loading: boolean
  error: string | null

  // Actions
  fetchSettings: () => Promise<void>
  updateLLMSettings: (llm: Partial<LLMSettings>) => Promise<void>
  updateTheme: (theme: 'light' | 'dark' | 'system') => void
  updateLanguage: (language: 'zh-CN' | 'en-US') => void
}

const defaultSettings: AppSettings = {
  llm: {
    baseUrl: 'https://api.openai.com/v1',
    apiKey: '',
    model: 'gpt-4'
  },
  theme: 'system',
  language: 'zh-CN'
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      settings: defaultSettings,
      loading: false,
      error: null,

      fetchSettings: async () => {
        set({ loading: true, error: null })
        try {
          // TODO: 调用后端 API
          // const settings = await apiClient.getSettings()
          // set({ settings, loading: false })
          set({ loading: false })
        } catch (error) {
          set({ error: (error as Error).message, loading: false })
        }
      },

      updateLLMSettings: async (llm) => {
        set({ loading: true, error: null })
        try {
          // TODO: 调用后端 API
          // await apiClient.updateLLMSettings(llm)
          set((state) => ({
            settings: {
              ...state.settings,
              llm: { ...state.settings.llm, ...llm }
            },
            loading: false
          }))
        } catch (error) {
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
