import { pyInvoke } from 'tauri-plugin-pytauri-api'

import { isTauri } from '@/lib/utils/tauri'

export interface SystemResponse<T = unknown> {
  success: boolean
  message?: string
  data?: T
  error?: string
  timestamp?: string
}

async function invokeSystem<T = SystemResponse>(command: string, args?: any): Promise<T | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return await pyInvoke<T>(command, args)
  } catch (error) {
    console.error(`[system] 调用 ${command} 失败:`, error)
    throw error
  }
}

export async function startBackend(): Promise<SystemResponse | null> {
  return await invokeSystem<SystemResponse>('start_system')
}

export async function stopBackend(): Promise<SystemResponse | null> {
  return await invokeSystem<SystemResponse>('stop_system')
}

export async function fetchBackendStats(): Promise<SystemResponse | null> {
  return await invokeSystem<SystemResponse>('get_system_stats')
}

export async function fetchLLMStats(): Promise<SystemResponse | null> {
  return await invokeSystem<SystemResponse>('get_llm_stats')
}

export async function recordLLMUsage(params: {
  model: string
  promptTokens: number
  completionTokens: number
  totalTokens: number
  cost?: number
  requestType: string
}): Promise<SystemResponse | null> {
  return await invokeSystem<SystemResponse>('record_llm_usage', params)
}
