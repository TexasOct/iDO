// 设置相关类型定义
// 注意：LLM 模型配置已迁移到 multi-model 管理系统
// 参见 src/lib/types/models.ts 和 src/lib/stores/models.ts

export interface DatabaseSettings {
  path?: string
}

export interface ScreenshotSettings {
  savePath?: string
}

// 多显示器信息
export interface MonitorInfo {
  index: number
  name: string
  width: number
  height: number
  left: number
  top: number
  is_primary: boolean
  resolution: string
}

// 屏幕选择设置
export interface ScreenSetting {
  id?: number
  monitor_index: number
  monitor_name: string
  is_enabled: boolean
  resolution: string
  is_primary: boolean
  created_at?: string
  updated_at?: string
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
