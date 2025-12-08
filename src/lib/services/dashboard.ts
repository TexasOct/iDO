import {
  getLlmStats,
  getLlmStatsByModel,
  recordLlmUsage as apiRecordLlmUsage,
  getUsageSummary
} from '@/lib/client/apiClient'
import { isTauri } from '@/lib/utils/tauri'

export interface DashboardResponse<T = unknown> {
  success: boolean
  message?: string
  data?: T
  error?: string
  timestamp?: string
}

export async function fetchLLMStats(params?: { modelId?: string }): Promise<DashboardResponse | null> {
  if (!isTauri()) {
    return null
  }

  try {
    if (params?.modelId) {
      return await getLlmStatsByModel({ modelId: params.modelId })
    }
    return await getLlmStats()
  } catch (error) {
    console.error('[dashboard] Fetch LLM stats failed:', error)
    throw error
  }
}

export async function recordLLMUsage(params: {
  model: string
  promptTokens: number
  completionTokens: number
  totalTokens: number
  cost?: number
  requestType: string
}): Promise<DashboardResponse | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return await apiRecordLlmUsage(params)
  } catch (error) {
    console.error('[dashboard] Record LLM usage failed:', error)
    throw error
  }
}

export async function fetchUsageSummary(): Promise<DashboardResponse | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return await getUsageSummary()
  } catch (error) {
    console.error('[dashboard] Fetch usage summary failed:', error)
    throw error
  }
}
