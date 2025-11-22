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
  streamingMessages: Record<string, string> // conversationId -> streaming message content (后端通过事件推送)

  // 本地 UI 状态（支持多会话同时发送）
  sendingConversationIds: Set<string> // 正在发送消息、等待后端响应的会话集合

  // 活动关联上下文
  pendingActivityId: string | null // 待关联的活动ID

  // 待发送消息和图片
  pendingMessage: string | null // 待填充到输入框的消息
  pendingImages: string[] // 待填充到输入框的图片

  // 待发送的数据（来自其他模块）
  pendingExternalData: any | null

  // 加载状态
  loading: boolean
  loadingMessages: boolean // 正在加载当前会话的消息

  // Actions
  setCurrentConversation: (conversationId: string | null) => void
  setPendingActivityId: (activityId: string | null) => void
  setPendingMessage: (message: string | null) => void
  setPendingImages: (images: string[]) => void
  setPendingExternalData: (data: any | null) => void
  fetchConversations: () => Promise<void>
  refreshConversations: () => Promise<void>
  fetchMessages: (conversationId: string) => Promise<void>
  createConversation: (title: string, relatedActivityIds?: string[], modelId?: string | null) => Promise<Conversation>
  createConversationFromActivities: (activityIds: string[]) => Promise<string>
  sendMessage: (conversationId: string, content: string, images?: string[], modelId?: string | null) => Promise<void>
  deleteConversation: (conversationId: string) => Promise<void>

  // 流式消息处理
  appendStreamingChunk: (conversationId: string, chunk: string) => void
  setStreamingComplete: (conversationId: string, messageId?: string) => void
  resetStreaming: (conversationId: string) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => {
      // 每个会话独立的待处理消息块和调度器
      const pendingChunksMap = new Map<string, string>()
      const rafIdMap = new Map<string, number>()
      const timeoutIdMap = new Map<string, ReturnType<typeof setTimeout>>()

      const clearScheduledFlush = (conversationId: string) => {
        const rafId = rafIdMap.get(conversationId)
        const timeoutId = timeoutIdMap.get(conversationId)

        if (rafId !== undefined && typeof window !== 'undefined' && typeof window.cancelAnimationFrame === 'function') {
          window.cancelAnimationFrame(rafId)
        }
        if (timeoutId !== undefined) {
          clearTimeout(timeoutId)
        }
        rafIdMap.delete(conversationId)
        timeoutIdMap.delete(conversationId)
      }

      const flushPendingChunks = (conversationId: string) => {
        const pendingChunks = pendingChunksMap.get(conversationId) || ''
        if (!pendingChunks) {
          rafIdMap.delete(conversationId)
          timeoutIdMap.delete(conversationId)
          return
        }

        pendingChunksMap.set(conversationId, '')
        rafIdMap.delete(conversationId)
        timeoutIdMap.delete(conversationId)

        set((state) => {
          const previousContent = state.streamingMessages[conversationId] || ''
          const isFirstChunk = previousContent === ''

          // 如果是第一个块，从 sending 集合中移除该会话
          if (isFirstChunk && state.sendingConversationIds.has(conversationId)) {
            console.log(`[Chat] 收到第一个流式块，从 sending 状态中移除: ${conversationId}`)
            const newSendingIds = new Set(state.sendingConversationIds)
            newSendingIds.delete(conversationId)
            return {
              streamingMessages: {
                ...state.streamingMessages,
                [conversationId]: previousContent + pendingChunks
              },
              sendingConversationIds: newSendingIds
            }
          }

          return {
            streamingMessages: {
              ...state.streamingMessages,
              [conversationId]: previousContent + pendingChunks
            }
          }
        })
      }

      const scheduleFlush = (conversationId: string) => {
        const pendingChunks = pendingChunksMap.get(conversationId) || ''
        if (pendingChunks === '') return
        if (rafIdMap.has(conversationId) || timeoutIdMap.has(conversationId)) return

        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          const rafId = window.requestAnimationFrame(() => flushPendingChunks(conversationId))
          rafIdMap.set(conversationId, rafId)
        } else {
          const timeoutId = setTimeout(() => flushPendingChunks(conversationId), 16)
          timeoutIdMap.set(conversationId, timeoutId)
        }
      }

      return {
        // 初始状态
        conversations: [],
        messages: {},
        currentConversationId: null,
        streamingMessages: {},
        sendingConversationIds: new Set<string>(),
        pendingActivityId: null,
        pendingMessage: null,
        pendingImages: [],
        pendingExternalData: null,
        loading: false,
        loadingMessages: false,

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

        // 设置待发送的图片
        setPendingImages: (images) => {
          set({ pendingImages: images })
        },

        // 设置待发送的外部数据
        setPendingExternalData: (data) => {
          set({ pendingExternalData: data })
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
          set({ loadingMessages: true })
          try {
            const messages = await chatService.getMessages({
              conversationId,
              limit: 100
            })

            // 转换 metadata.error 为 error 字段
            const transformedMessages = messages.map((msg) => {
              if (msg.metadata?.error) {
                return {
                  ...msg,
                  error: msg.content
                }
              }
              return msg
            })

            set((state) => ({
              messages: {
                ...state.messages,
                [conversationId]: transformedMessages
              },
              loadingMessages: false
            }))
          } catch (error) {
            console.error('获取消息列表失败:', error)
            set({ loadingMessages: false })
          }
        },

        // 创建对话
        createConversation: async (title, relatedActivityIds, modelId) => {
          set({ loading: true })
          try {
            const conversation = await chatService.createConversation({
              title,
              relatedActivityIds,
              modelId
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
        sendMessage: async (conversationId, content, images, modelId) => {
          console.log(`[Chat] 开始发送消息，添加到 sending 状态: ${conversationId}`)
          set((state) => {
            const newSendingIds = new Set(state.sendingConversationIds)
            newSendingIds.add(conversationId)
            return {
              sendingConversationIds: newSendingIds,
              streamingMessages: {
                ...state.streamingMessages,
                [conversationId]: '' // 预先清空流式消息
              }
            }
          })

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
            await chatService.sendMessage(conversationId, content, images, modelId)
            // Note: localSendingConversationId 会在收到第一个流式消息块时被清除
          } catch (error) {
            console.error('发送消息失败:', error)

            // 添加错误消息到 UI
            const errorContent = error instanceof Error ? error.message : String(error)
            const errorMessage: Message = {
              id: `error-${Date.now()}`,
              conversationId,
              role: 'assistant',
              content: errorContent,
              timestamp: Date.now(),
              error: errorContent,
              metadata: { error: true, error_type: 'network' }
            }

            set((state) => {
              const existingMessages = state.messages[conversationId] || []
              const newStreamingMessages = { ...state.streamingMessages }
              delete newStreamingMessages[conversationId]

              // 从 sending 集合中移除该会话
              const newSendingIds = new Set(state.sendingConversationIds)
              newSendingIds.delete(conversationId)

              return {
                messages: {
                  ...state.messages,
                  [conversationId]: [...existingMessages, errorMessage]
                },
                streamingMessages: newStreamingMessages,
                sendingConversationIds: newSendingIds
              }
            })
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
        appendStreamingChunk: (conversationId, chunk) => {
          const currentChunks = pendingChunksMap.get(conversationId) || ''
          pendingChunksMap.set(conversationId, currentChunks + chunk)
          scheduleFlush(conversationId)
        },

        // 流式消息完成
        setStreamingComplete: async (conversationId, messageId) => {
          clearScheduledFlush(conversationId)

          // 刷新该会话的待处理消息块
          const pendingChunks = pendingChunksMap.get(conversationId) || ''
          if (pendingChunks) {
            flushPendingChunks(conversationId)
          }

          const { streamingMessages } = get()
          const streamingMessage = streamingMessages[conversationId] || ''

          // 将流式消息保存到消息列表
          if (streamingMessage) {
            const assistantMessage: Message = {
              id: messageId || `msg-${Date.now()}`,
              conversationId,
              role: 'assistant',
              content: streamingMessage,
              timestamp: Date.now()
            }

            set((state) => {
              const newStreamingMessages = { ...state.streamingMessages }
              delete newStreamingMessages[conversationId]

              // 从 sending 集合中移除该会话（如果还在）
              const newSendingIds = new Set(state.sendingConversationIds)
              newSendingIds.delete(conversationId)

              return {
                messages: {
                  ...state.messages,
                  [conversationId]: [...(state.messages[conversationId] || []), assistantMessage]
                },
                streamingMessages: newStreamingMessages,
                sendingConversationIds: newSendingIds
              }
            })
          } else {
            // 没有流式消息，重新获取消息列表
            await get().fetchMessages(conversationId)
            set((state) => {
              const newStreamingMessages = { ...state.streamingMessages }
              delete newStreamingMessages[conversationId]

              // 从 sending 集合中移除该会话（如果还在）
              const newSendingIds = new Set(state.sendingConversationIds)
              newSendingIds.delete(conversationId)

              return {
                streamingMessages: newStreamingMessages,
                sendingConversationIds: newSendingIds
              }
            })
          }

          // 清理该会话的待处理数据
          pendingChunksMap.delete(conversationId)

          await get().refreshConversations()
        },

        // 重置流式状态
        resetStreaming: (conversationId) => {
          clearScheduledFlush(conversationId)
          pendingChunksMap.delete(conversationId)

          set((state) => {
            const newStreamingMessages = { ...state.streamingMessages }
            delete newStreamingMessages[conversationId]

            return {
              streamingMessages: newStreamingMessages
              // 不需要清除其他状态，streamingMessages 的存在即表示状态
            }
          })
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
