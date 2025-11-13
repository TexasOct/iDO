/**
 * Chat Zustand Store
 * 管理对话和消息状态
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Conversation, Message } from '@/lib/types/chat'
import * as chatService from '@/lib/services/chat'

export const DEFAULT_CHAT_TITLE = '新对话'
const AUTO_TITLE_MAX_LENGTH = 28

const MARKDOWN_CODE_BLOCK = /```[\s\S]*?```/g
const INLINE_CODE = /`([^`]+)`/g
const LEADING_MARKERS = /^[#>*\-\s]+/

function generateAutoTitleCandidate(text: string | undefined, maxLength = AUTO_TITLE_MAX_LENGTH): string | null {
  if (!text) return null
  let cleaned = text.trim()
  if (!cleaned) return null

  cleaned = cleaned.replace(MARKDOWN_CODE_BLOCK, ' ')
  cleaned = cleaned.replace(INLINE_CODE, (_, content) => content)
  cleaned = cleaned.replace(LEADING_MARKERS, '')
  cleaned = cleaned
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^[-_]+/, '')
    .replace(/[-_]+$/, '')

  if (!cleaned) return null
  if (cleaned.length <= maxLength) return cleaned

  const truncated = cleaned.slice(0, maxLength - 1).trim()
  return truncated ? `${truncated}…` : null
}

interface ChatState {
  // 数据状态
  conversations: Conversation[]
  messages: Record<string, Message[]> // conversationId -> messages
  currentConversationId: string | null
  streamingMessage: string // 当前流式输出的消息内容
  isStreaming: boolean

  // 活动关联上下文
  pendingActivityId: string | null // 待关联的活动ID

  // 待发送消息
  pendingMessage: string | null // 待填充到输入框的消息

  // 加载状态
  loading: boolean
  sending: boolean

  // Actions
  setCurrentConversation: (conversationId: string | null) => void
  setPendingActivityId: (activityId: string | null) => void
  setPendingMessage: (message: string | null) => void
  fetchConversations: () => Promise<void>
  refreshConversations: () => Promise<void>
  fetchMessages: (conversationId: string) => Promise<void>
  createConversation: (title: string, relatedActivityIds?: string[]) => Promise<Conversation>
  createConversationFromActivities: (activityIds: string[]) => Promise<string>
  sendMessage: (conversationId: string, content: string, images?: string[]) => Promise<void>
  deleteConversation: (conversationId: string) => Promise<void>

  // 流式消息处理
  appendStreamingChunk: (chunk: string) => void
  setStreamingComplete: (conversationId: string, messageId?: string) => void
  resetStreaming: () => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => {
      let pendingChunks = ''
      let rafId: number | null = null
      let timeoutId: ReturnType<typeof setTimeout> | null = null

      const clearScheduledFlush = () => {
        if (rafId !== null && typeof window !== 'undefined' && typeof window.cancelAnimationFrame === 'function') {
          window.cancelAnimationFrame(rafId)
        }
        if (timeoutId !== null) {
          clearTimeout(timeoutId)
        }
        rafId = null
        timeoutId = null
      }

      const flushPendingChunks = () => {
        if (!pendingChunks) {
          rafId = null
          timeoutId = null
          return
        }

        const chunkToAppend = pendingChunks
        pendingChunks = ''
        rafId = null
        timeoutId = null

        set((state) => ({
          streamingMessage: state.streamingMessage + chunkToAppend
        }))
      }

      const scheduleFlush = () => {
        if (pendingChunks === '') return
        if (rafId !== null || timeoutId !== null) return

        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          rafId = window.requestAnimationFrame(flushPendingChunks)
        } else {
          timeoutId = setTimeout(flushPendingChunks, 16)
        }
      }

      return {
        // 初始状态
        conversations: [],
        messages: {},
        currentConversationId: null,
        streamingMessage: '',
        isStreaming: false,
        pendingActivityId: null,
        pendingMessage: null,
        loading: false,
        sending: false,

        // 设置当前对话
        setCurrentConversation: (conversationId) => {
          set({ currentConversationId: conversationId })
        },

        // 设置待关联的活动ID
        setPendingActivityId: (activityId) => {
          set({ pendingActivityId: activityId })
        },

        // 设置待发送的消息
        setPendingMessage: (message) => {
          set({ pendingMessage: message })
        },

        // 获取对话列表
        fetchConversations: async () => {
          set({ loading: true })
          try {
            const conversations = await chatService.getConversations({ limit: 50 })
            set({ conversations, loading: false })
          } catch (error) {
            console.error('获取对话列表失败:', error)
            set({ loading: false })
          }
        },

        refreshConversations: async () => {
          try {
            const conversations = await chatService.getConversations({ limit: 50 })
            set({ conversations })
          } catch (error) {
            console.error('刷新对话列表失败:', error)
          }
        },

        // 获取消息列表
        fetchMessages: async (conversationId) => {
          set({ loading: true })
          try {
            const messages = await chatService.getMessages({
              conversationId,
              limit: 100
            })

            set((state) => ({
              messages: {
                ...state.messages,
                [conversationId]: messages
              },
              loading: false
            }))
          } catch (error) {
            console.error('获取消息列表失败:', error)
            set({ loading: false })
          }
        },

        // 创建对话
        createConversation: async (title, relatedActivityIds) => {
          set({ loading: true })
          try {
            const conversation = await chatService.createConversation({
              title,
              relatedActivityIds
            })

            set((state) => ({
              conversations: [conversation, ...state.conversations],
              currentConversationId: conversation.id,
              loading: false
            }))

            return conversation
          } catch (error) {
            console.error('创建对话失败:', error)
            set({ loading: false })
            throw error
          }
        },

        // 从活动创建对话
        createConversationFromActivities: async (activityIds) => {
          set({ loading: true })
          try {
            const result = await chatService.createConversationFromActivities(activityIds)

            // 重新获取对话列表
            await get().fetchConversations()

            // 设置为当前对话
            set({
              currentConversationId: result.conversationId,
              loading: false
            })

            // 加载消息
            await get().fetchMessages(result.conversationId)

            return result.conversationId
          } catch (error) {
            console.error('从活动创建对话失败:', error)
            set({ loading: false })
            throw error
          }
        },

        // 发送消息
        sendMessage: async (conversationId, content, images) => {
          set({ sending: true, isStreaming: true, streamingMessage: '' })

          try {
            // 立即添加用户消息到 UI
            const userMessage: Message = {
              id: `temp-${Date.now()}`,
              conversationId,
              role: 'user',
              content,
              timestamp: Date.now(),
              images: images || []
            }

            set((state) => {
              const existingMessages = state.messages[conversationId] || []
              const messages = {
                ...state.messages,
                [conversationId]: [...existingMessages, userMessage]
              }

              let conversationsChanged = false
              const conversations = state.conversations.map((conv) => {
                if (conv.id !== conversationId) return conv

                const shouldAutoTitle = conv.metadata?.autoTitle !== false && conv.metadata?.titleFinalized !== true
                if (!shouldAutoTitle) return conv

                const generatedTitle = generateAutoTitleCandidate(content)
                if (!generatedTitle || generatedTitle === conv.title) return conv

                conversationsChanged = true
                return {
                  ...conv,
                  title: generatedTitle,
                  updatedAt: Date.now(),
                  metadata: {
                    ...(conv.metadata ?? {}),
                    autoTitle: false,
                    titleFinalized: true,
                    generatedTitleSource: 'auto',
                    generatedTitlePreview: generatedTitle
                  }
                }
              })

              return conversationsChanged ? { messages, conversations } : { messages }
            })

            // 调用后端 API（后端会通过 Tauri Events 发送流式响应）
            await chatService.sendMessage(conversationId, content, images)

            set({ sending: false })
          } catch (error) {
            console.error('发送消息失败:', error)
            set({ sending: false, isStreaming: false })
            throw error
          }
        },

        // 删除对话
        deleteConversation: async (conversationId) => {
          set({ loading: true })
          try {
            await chatService.deleteConversation(conversationId)

            set((state) => ({
              conversations: state.conversations.filter((c) => c.id !== conversationId),
              messages: Object.fromEntries(Object.entries(state.messages).filter(([id]) => id !== conversationId)),
              currentConversationId:
                state.currentConversationId === conversationId ? null : state.currentConversationId,
              loading: false
            }))
          } catch (error) {
            console.error('删除对话失败:', error)
            set({ loading: false })
            throw error
          }
        },

        // 追加流式消息块
        appendStreamingChunk: (chunk) => {
          pendingChunks += chunk
          scheduleFlush()
        },

        // 流式消息完成
        setStreamingComplete: async (conversationId, messageId) => {
          clearScheduledFlush()
          if (pendingChunks) {
            flushPendingChunks()
          }

          const { streamingMessage } = get()

          // 将流式消息保存到消息列表
          if (streamingMessage) {
            const assistantMessage: Message = {
              id: messageId || `msg-${Date.now()}`,
              conversationId,
              role: 'assistant',
              content: streamingMessage,
              timestamp: Date.now()
            }

            set((state) => ({
              messages: {
                ...state.messages,
                [conversationId]: [...(state.messages[conversationId] || []), assistantMessage]
              },
              isStreaming: false,
              streamingMessage: ''
            }))
          } else {
            // 没有流式消息，重新获取消息列表
            await get().fetchMessages(conversationId)
            set({ isStreaming: false, streamingMessage: '' })
          }

          await get().refreshConversations()
        },

        // 重置流式状态
        resetStreaming: () => {
          clearScheduledFlush()
          pendingChunks = ''
          set({ isStreaming: false, streamingMessage: '' })
        }
      }
    },
    {
      name: 'chat-storage',
      partialize: (state) => ({
        currentConversationId: state.currentConversationId
        // 不持久化 conversations 和 messages，每次启动重新加载
      })
    }
  )
)
