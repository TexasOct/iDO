// 设置相关类型定义
// 注意：LLM 模型配置已迁移到 multi-model 管理系统
// 参见 src/lib/types/models.ts 和 src/lib/stores/models.ts

export interface DatabaseSettings {
  path?: string
}

export interface ScreenshotSettings {
  savePath?: string
}

export interface FriendlyChatSettings {
  enabled: boolean
  interval: number // minutes (5-120)
  dataWindow: number // minutes (5-120)
  enableSystemNotification: boolean
  enableLive2dDisplay: boolean
}

export interface AppSettings {
  database?: DatabaseSettings
  screenshot?: ScreenshotSettings
  theme: 'light' | 'dark' | 'system'
  language: 'zh-CN' | 'en-US'
  friendlyChat?: FriendlyChatSettings
}
