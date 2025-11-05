// Friendly Chat types

export interface FriendlyChatMessage {
  id: string
  message: string
  timestamp: string
  createdAt: string
}

export interface FriendlyChatSettings {
  enabled: boolean
  interval: number // minutes (5-120)
  dataWindow: number // minutes (5-120)
  enableSystemNotification: boolean
  enableLive2dDisplay: boolean
}

export interface FriendlyChatHistoryResponse {
  messages: FriendlyChatMessage[]
  count: number
}
