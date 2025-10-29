import { pyInvoke } from 'tauri-plugin-pytauri-api'
import { isTauri } from '@/lib/utils/tauri'

export interface DashboardResponse<T = unknown> {
  success: boolean
  message?: string
  data?: T
  error?: string
  timestamp?: string
}

async function invokeDashboard<T = DashboardResponse>(command: string, args?: any): Promise<T | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return await pyInvoke<T>(command, args)
  } catch (error) {
    console.error(`[dashboard] 调用 ${command} 失败:`, error)
    throw error
  }
}

export async function fetchLLMStats(params?: { modelId?: string }): Promise<DashboardResponse | null> {
  if (params?.modelId) {
    return await invokeDashboard<DashboardResponse>('get_llm_stats_by_model', {
      modelId: params.modelId
    })
  }

  return await invokeDashboard<DashboardResponse>('get_llm_stats')
}

export async function recordLLMUsage(params: {
  model: string
  promptTokens: number
  completionTokens: number
  totalTokens: number
  cost?: number
  requestType: string
}): Promise<DashboardResponse | null> {
  return await invokeDashboard<DashboardResponse>('record_llm_usage', params)
}

export async function fetchUsageSummary(): Promise<DashboardResponse | null> {
  return await invokeDashboard<DashboardResponse>('get_usage_summary')
}
