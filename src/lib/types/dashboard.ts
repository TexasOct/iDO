// 统计面板相关类型定义

export interface TokenUsageData {
  timestamp: number
  tokens: number
  model?: string
}

export interface AgentTaskData {
  timestamp: number
  completed: number
  failed: number
  total: number
}

export interface LLMModelPricing {
  id: string
  name: string
  provider: string
  model: string
  currency: string
  inputTokenPrice: number
  outputTokenPrice: number
}

export interface LLMUsageResponse {
  totalTokens: number
  totalCalls: number
  totalCost: number
  modelsUsed: string[]
  period: string
  dailyUsage: Array<{
    date: string
    tokens: number
    calls: number
    cost: number
  }>
  modelDetails?: LLMModelPricing | null
}

export interface DashboardMetrics {
  tokenUsage: TokenUsageData[]
  agentTasks: AgentTaskData[]
  period: 'day' | 'week' | 'month'
  llmStats?: LLMUsageResponse
}

export type TrendDimension = 'day' | 'week' | 'month' | 'custom'

export interface TrendRange {
  startDate: string
  endDate: string
}

export interface TrendDataPoint {
  date: string
  bucketStart: string
  bucketEnd: string
  tokens: number
  promptTokens: number
  completionTokens: number
  calls: number
  cost: number
}
