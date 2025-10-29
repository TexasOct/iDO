// 设置相关类型定义

export interface LLMSettings {
  provider: string
  baseUrl: string
  apiKey: string
  model: string
}

export interface DatabaseSettings {
  path?: string
}

export interface ScreenshotSettings {
  savePath?: string
}

export interface AppSettings {
  llm: LLMSettings
  database?: DatabaseSettings
  screenshot?: ScreenshotSettings
  theme: 'light' | 'dark' | 'system'
  language: 'zh-CN' | 'en-US'
}
