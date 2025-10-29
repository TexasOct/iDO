// LLM Models management types

export interface LLMModel {
  id: string
  name: string
  provider: string
  apiUrl: string
  model: string
  inputTokenPrice: number
  outputTokenPrice: number
  currency: string
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface CreateModelInput {
  name: string
  provider: string
  apiUrl: string
  model: string
  inputTokenPrice: number
  outputTokenPrice: number
  currency: string
  apiKey: string
}

export interface UpdateModelInput {
  modelId: string
  name?: string
  inputTokenPrice?: number
  outputTokenPrice?: number
  currency?: string
  apiKey?: string
}

export interface SelectModelInput {
  modelId: string
}

export interface ModelResponse<T = any> {
  success: boolean
  message: string
  data?: T
  timestamp?: string
}
