import { create } from 'zustand'
import { DashboardMetrics, LLMUsageResponse } from '@/lib/types/dashboard'
import { fetchLLMStats } from '@/lib/services/dashboard'

type ModelSelection = 'all' | string

interface DashboardState {
  metrics: DashboardMetrics
  loading: boolean
  error: string | null
  selectedModelId: ModelSelection

  // Actions
  fetchMetrics: (period: 'day' | 'week' | 'month') => Promise<void>
  setPeriod: (period: 'day' | 'week' | 'month') => void
  fetchLLMStats: (modelId?: string) => Promise<void>
  setSelectedModelId: (modelId: ModelSelection) => Promise<void>
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  metrics: {
    tokenUsage: [],
    agentTasks: [],
    period: 'day'
  },
  loading: false,
  error: null,
  selectedModelId: 'all',

  fetchMetrics: async (period) => {
    set({ loading: true, error: null })
    try {
      const { selectedModelId } = get()
      const modelId = selectedModelId === 'all' ? undefined : selectedModelId

      // 获取LLM统计数据（根据当前模型筛选）
      await get().fetchLLMStats(modelId)

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

  fetchLLMStats: async (modelId) => {
    try {
      const response = await fetchLLMStats(modelId ? { modelId } : undefined)

      if (response?.success && response.data) {
        set((state) => ({
          metrics: {
            ...state.metrics,
            llmStats: response.data as LLMUsageResponse
          },
          error: null
        }))
      } else if (response && !response.success) {
        set({ error: response.message ?? 'Failed to fetch LLM stats' })
      }
    } catch (error) {
      console.error('Failed to fetch LLM stats:', error)
      set({ error: (error as Error).message })
    }
  },

  setSelectedModelId: async (modelId) => {
    set({ selectedModelId: modelId, loading: true, error: null })
    try {
      const targetId = modelId === 'all' ? undefined : modelId
      await get().fetchLLMStats(targetId)
      set({ loading: false })
    } catch (error) {
      set({
        error: (error as Error).message ?? 'Failed to update model filter',
        loading: false
      })
    }
  }
}))
