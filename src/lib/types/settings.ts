// 设置相关类型定义

export interface LLMSettings {
  baseUrl: string
  apiKey: string
  model: string
}

export interface AppSettings {
  llm: LLMSettings
  theme: 'light' | 'dark' | 'system'
  language: 'zh-CN' | 'en-US'
}
