import { create } from 'zustand'
import { DashboardMetrics, LLMUsageResponse, TrendDataPoint, TrendDimension, TrendRange } from '@/lib/types/dashboard'
import { fetchLLMStats } from '@/lib/services/dashboard'
import * as apiClient from '@/lib/client/apiClient'
import { getDefaultRangeForDimension } from '@/lib/utils/date-range'

type ModelSelection = 'all' | string

interface DashboardState {
  metrics: DashboardMetrics
  loading: boolean
  error: string | null
  selectedModelId: ModelSelection
  trendDimension: TrendDimension
  trendRange: TrendRange
  trendData: TrendDataPoint[]
  trendLoading: boolean

  // Actions
  fetchMetrics: (period: 'day' | 'week' | 'month') => Promise<void>
  setPeriod: (period: 'day' | 'week' | 'month') => void
  fetchLLMStats: (modelId?: string) => Promise<void>
  setSelectedModelId: (modelId: ModelSelection) => Promise<void>
  setTrendDimension: (dimension: TrendDimension) => Promise<void>
  setTrendRange: (range: TrendRange) => Promise<void>
  fetchTrendData: (dimension: TrendDimension, range: TrendRange, modelId?: string) => Promise<void>
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
  trendDimension: 'day',
  trendRange: getDefaultRangeForDimension('day'),
  trendData: [],
  trendLoading: false,

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
      // Also fetch trend data for the new model
      await get().fetchTrendData(get().trendDimension, get().trendRange, targetId)
      set({ loading: false })
    } catch (error) {
      set({
        error: (error as Error).message ?? 'Failed to update model filter',
        loading: false
      })
    }
  },

  setTrendDimension: async (dimension) => {
    const nextRange = getDefaultRangeForDimension(dimension)
    set({ trendDimension: dimension, trendRange: nextRange })
    const { selectedModelId } = get()
    const modelId = selectedModelId === 'all' ? undefined : selectedModelId
    await get().fetchTrendData(dimension, nextRange, modelId)
  },

  setTrendRange: async (range) => {
    set({ trendRange: range })
    const { trendDimension, selectedModelId } = get()
    const modelId = selectedModelId === 'all' ? undefined : selectedModelId
    await get().fetchTrendData(trendDimension, range, modelId)
  },

  fetchTrendData: async (dimension, range, modelId) => {
    set({ trendLoading: true, error: null })
    try {
      const toDate = (value: string) => new Date(value)
      const rangeStart = toDate(range.startDate)
      const rangeEnd = toDate(range.endDate)
      const diffMs = Math.max(rangeEnd.getTime() - rangeStart.getTime(), 0)
      const rangeDays = Math.max(1, Math.floor(diffMs / (1000 * 60 * 60 * 24)) + 1)

      type LlmTrendRequest = Parameters<typeof apiClient.getLlmUsageTrend>[0] & {
        startDate?: string
        endDate?: string
      }

      const response = await apiClient.getLlmUsageTrend({
        dimension,
        days: rangeDays,
        modelConfigId: modelId,
        startDate: range.startDate,
        endDate: range.endDate
      } as LlmTrendRequest)

      if (response?.success && response.data) {
        set({
          trendData: response.data as TrendDataPoint[],
          trendLoading: false,
          error: null
        })
      } else if (response && !response.success) {
        const errorMessage = typeof response.message === 'string' ? response.message : 'Failed to fetch trend data'
        set({
          trendData: [],
          trendLoading: false,
          error: errorMessage
        })
      }
    } catch (error) {
      console.error('Failed to fetch trend data:', error)
      set({
        trendData: [],
        trendLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch trend data'
      })
    }
  }
}))
