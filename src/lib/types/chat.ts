/**
 * Chat-related type definitions
 */

export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  id: string
  conversationId: string
  role: MessageRole
  content: string
  timestamp: number // Timestamp in milliseconds
  metadata?: Record<string, any>
  images?: string[] // Base64 encoded images (data:image/jpeg;base64,...)
  error?: string // Error message if the request failed
}

export interface Conversation {
  id: string
  title: string
  createdAt: number // Timestamp in milliseconds
  updatedAt: number // Timestamp in milliseconds
  relatedActivityIds?: string[]
  metadata?: Record<string, any>
  modelId?: string | null // Model ID used for the conversation
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
