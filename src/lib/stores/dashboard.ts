import { create } from 'zustand'
import { DashboardMetrics } from '@/lib/types/dashboard'

interface DashboardState {
  metrics: DashboardMetrics
  loading: boolean
  error: string | null

  // Actions
  fetchMetrics: (period: 'day' | 'week' | 'month') => Promise<void>
  setPeriod: (period: 'day' | 'week' | 'month') => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
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
      // TODO: 调用后端 API
      // const metrics = await apiClient.getMetrics(period)
      set({
        metrics: {
          tokenUsage: [],
          agentTasks: [],
          period
        },
        loading: false
      })
    } catch (error) {
      set({ error: (error as Error).message, loading: false })
    }
  },

  setPeriod: (period) =>
    set((state) => ({
      metrics: { ...state.metrics, period }
    }))
}))
