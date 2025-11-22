/**
 * Chat 相关类型定义
 */

export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  id: string
  conversationId: string
  role: MessageRole
  content: string
  timestamp: number // 毫秒时间戳
  metadata?: Record<string, any>
  images?: string[] // Base64 encoded images (data:image/jpeg;base64,...)
  error?: string // Error message if the request failed
}

export interface Conversation {
  id: string
  title: string
  createdAt: number // 毫秒时间戳
  updatedAt: number // 毫秒时间戳
  relatedActivityIds?: string[]
  metadata?: Record<string, any>
  modelId?: string | null // 对话使用的模型ID
}

export interface ChatMessageChunk {
  conversationId: string
  chunk: string
  done: boolean
  messageId?: string
}

export interface ConversationWithLastMessage extends Conversation {
  lastMessage?: Message
  messageCount?: number
}
