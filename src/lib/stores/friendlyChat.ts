import { create } from 'zustand'
import type { FriendlyChatSettings, FriendlyChatMessage } from '@/lib/types/friendlyChat'
import {
  getFriendlyChatSettings,
  updateFriendlyChatSettings,
  getFriendlyChatHistory,
  triggerFriendlyChat
} from '@/lib/client/apiClient'

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
      console.log('[FriendlyChat] Fetching settings...')
      const response: any = await getFriendlyChatSettings()

      if (response.success && response.data) {
        const settings: FriendlyChatSettings = {
          enabled: response.data.enabled ?? defaultSettings.enabled,
          interval: response.data.interval ?? defaultSettings.interval,
          dataWindow: response.data.dataWindow ?? defaultSettings.dataWindow,
          enableSystemNotification: response.data.enableSystemNotification ?? defaultSettings.enableSystemNotification,
          enableLive2dDisplay: response.data.enableLive2dDisplay ?? defaultSettings.enableLive2dDisplay
        }
        set({ settings, loading: false })
      } else {
        throw new Error('Failed to fetch settings')
      }
    } catch (error) {
      console.error('Failed to fetch friendly chat settings:', error)
      set({ error: (error as Error).message, loading: false, settings: defaultSettings })
    }
  },

  updateSettings: async (updates: Partial<FriendlyChatSettings>) => {
    set({ loading: true, error: null })
    try {
      console.log('[FriendlyChat] Updating settings:', updates)
      const response: any = await updateFriendlyChatSettings(updates)

      if (response.success && response.data) {
        const settings: FriendlyChatSettings = {
          enabled: response.data.enabled ?? defaultSettings.enabled,
          interval: response.data.interval ?? defaultSettings.interval,
          dataWindow: response.data.dataWindow ?? defaultSettings.dataWindow,
          enableSystemNotification: response.data.enableSystemNotification ?? defaultSettings.enableSystemNotification,
          enableLive2dDisplay: response.data.enableLive2dDisplay ?? defaultSettings.enableLive2dDisplay
        }
        set({ settings, loading: false })
      } else {
        throw new Error(response.message || 'Failed to update settings')
      }
    } catch (error) {
      console.error('Failed to update friendly chat settings:', error)
      set({ error: (error as Error).message, loading: false })
      // Re-fetch to ensure consistency
      await get().fetchSettings()
    }
  },

  fetchHistory: async (limit = 20, offset = 0) => {
    set({ loading: true, error: null })
    try {
      console.log('[FriendlyChat] Fetching history...', { limit, offset })
      const response: any = await getFriendlyChatHistory({ limit, offset })

      if (response.success && response.data) {
        set({ messages: response.data.messages || [], loading: false })
      } else {
        throw new Error('Failed to fetch history')
      }
    } catch (error) {
      console.error('Failed to fetch friendly chat history:', error)
      set({ error: (error as Error).message, loading: false, messages: [] })
    }
  },

  triggerChat: async () => {
    set({ loading: true, error: null })
    try {
      console.log('[FriendlyChat] Triggering immediate chat...')
      const response: any = await triggerFriendlyChat()

      set({ loading: false })

      if (response.success && response.data?.chatMessage) {
        return response.data.chatMessage
      } else {
        console.warn('Failed to generate chat message:', response.message)
        return null
      }
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
