import { create } from 'zustand'
import { DashboardMetrics, LLMUsageResponse } from '@/lib/types/dashboard'
import { fetchLLMStats } from '@/lib/services/dashboard'

interface DashboardState {
  metrics: DashboardMetrics
  loading: boolean
  error: string | null

  // Actions
  fetchMetrics: (period: 'day' | 'week' | 'month') => Promise<void>
  setPeriod: (period: 'day' | 'week' | 'month') => void
  fetchLLMStats: () => Promise<void>
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  metrics: {
    tokenUsage: [],
    agentTasks: [],
    period: 'day'
  },
  loading: false,
  error: null,

  fetchMetrics: async (period) => {
    set({ loading: true, error: null })
    try {
      // 获取LLM统计数据
      await get().fetchLLMStats()

      set((state) => ({
        metrics: { ...state.metrics, period },
        loading: false
      }))
    } catch (error) {
      set({ error: (error as Error).message, loading: false })
    }
  },

  setPeriod: (period) =>
    set((state) => ({
      metrics: { ...state.metrics, period }
    })),

  fetchLLMStats: async () => {
    try {
      const response = await fetchLLMStats()

      if (response?.success && response.data) {
        set((state) => ({
          metrics: {
            ...state.metrics,
            llmStats: response.data as LLMUsageResponse
          }
        }))
      }
    } catch (error) {
      console.error('Failed to fetch LLM stats:', error)
      // 不抛出错误，只记录日志
    }
  }
}))
