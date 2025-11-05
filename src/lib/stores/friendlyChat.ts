import { create } from 'zustand'
import type { FriendlyChatSettings, FriendlyChatMessage } from '@/lib/types/friendlyChat'

interface FriendlyChatState {
  settings: FriendlyChatSettings
  messages: FriendlyChatMessage[]
  loading: boolean
  error: string | null

  // Actions
  fetchSettings: () => Promise<void>
  updateSettings: (settings: Partial<FriendlyChatSettings>) => Promise<void>
  fetchHistory: (limit?: number, offset?: number) => Promise<void>
  triggerChat: () => Promise<string | null>
  addMessage: (message: FriendlyChatMessage) => void
}

const defaultSettings: FriendlyChatSettings = {
  enabled: false,
  interval: 20,
  dataWindow: 20,
  enableSystemNotification: true,
  enableLive2dDisplay: true
}

export const useFriendlyChatStore = create<FriendlyChatState>((set, get) => ({
  settings: defaultSettings,
  messages: [],
  loading: false,
  error: null,

  fetchSettings: async () => {
    set({ loading: true, error: null })
    try {
      // TODO: Replace with actual API call when TypeScript client is generated
      // const response = await getFriendlyChatSettings()
      // For now, use default settings
      console.log('[FriendlyChat] Fetching settings...')
      set({ settings: defaultSettings, loading: false })
    } catch (error) {
      console.error('Failed to fetch friendly chat settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  updateSettings: async (updates: Partial<FriendlyChatSettings>) => {
    set({ loading: true, error: null })
    try {
      const currentSettings = get().settings
      const newSettings = { ...currentSettings, ...updates }

      // TODO: Replace with actual API call when TypeScript client is generated
      // const response = await updateFriendlyChatSettings(updates)
      console.log('[FriendlyChat] Updating settings:', updates)

      set({ settings: newSettings, loading: false })
    } catch (error) {
      console.error('Failed to update friendly chat settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  fetchHistory: async (limit = 20, offset = 0) => {
    set({ loading: true, error: null })
    try {
      // TODO: Replace with actual API call when TypeScript client is generated
      // const response = await getFriendlyChatHistory({ limit, offset })
      console.log('[FriendlyChat] Fetching history...', { limit, offset })
      set({ messages: [], loading: false })
    } catch (error) {
      console.error('Failed to fetch friendly chat history:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  triggerChat: async () => {
    set({ loading: true, error: null })
    try {
      // TODO: Replace with actual API call when TypeScript client is generated
      // const response = await triggerFriendlyChat()
      console.log('[FriendlyChat] Triggering immediate chat...')
      set({ loading: false })
      return null
    } catch (error) {
      console.error('Failed to trigger friendly chat:', error)
      set({ error: (error as Error).message, loading: false })
      return null
    }
  },

  addMessage: (message: FriendlyChatMessage) => {
    set((state) => ({
      messages: [message, ...state.messages]
    }))
  }
}))
