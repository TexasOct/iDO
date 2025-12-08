import { startSystem, stopSystem, getSystemStats, getLlmStats, recordLlmUsage } from '@/lib/client/apiClient'
import { isTauri } from '@/lib/utils/tauri'

export interface SystemResponse<T = unknown> {
  success: boolean
  message?: string
  data?: T
  error?: string
  timestamp?: string
}

export async function startBackend(): Promise<SystemResponse | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return (await startSystem()) as unknown as SystemResponse
  } catch (error) {
    console.error('[system] Start system failed:', error)
    throw error
  }
}

export async function stopBackend(): Promise<SystemResponse | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return (await stopSystem()) as unknown as SystemResponse
  } catch (error) {
    console.error('[system] Stop system failed:', error)
    throw error
  }
}

export async function fetchBackendStats(): Promise<SystemResponse | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return (await getSystemStats()) as unknown as SystemResponse
  } catch (error) {
    console.error('[system] Get system stats failed:', error)
    throw error
  }
}

export async function fetchLLMStats(): Promise<SystemResponse | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return await getLlmStats()
  } catch (error) {
    console.error('[system] Get LLM stats failed:', error)
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
}): Promise<SystemResponse | null> {
  if (!isTauri()) {
    return null
  }

  try {
    return await recordLlmUsage(params)
  } catch (error) {
    console.error('[system] Record LLM usage failed:', error)
    throw error
  }
}
