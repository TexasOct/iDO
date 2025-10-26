/**
 * Chat Zustand Store
 * 管理对话和消息状态
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Conversation, Message } from '@/lib/types/chat'
import * as chatService from '@/lib/services/chat'

interface ChatState {
  // 数据状态
  conversations: Conversation[]
  messages: Record<string, Message[]> // conversationId -> messages
  currentConversationId: string | null
  streamingMessage: string // 当前流式输出的消息内容
  isStreaming: boolean

  // 加载状态
  loading: boolean
  sending: boolean

  // Actions
  setCurrentConversation: (conversationId: string | null) => void
  fetchConversations: () => Promise<void>
  fetchMessages: (conversationId: string) => Promise<void>
  createConversation: (title: string, relatedActivityIds?: string[]) => Promise<Conversation>
  createConversationFromActivities: (activityIds: string[]) => Promise<string>
  sendMessage: (conversationId: string, content: string) => Promise<void>
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
        loading: false,
        sending: false,

        // 设置当前对话
        setCurrentConversation: (conversationId) => {
          set({ currentConversationId: conversationId })
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
        sendMessage: async (conversationId, content) => {
          set({ sending: true, isStreaming: true, streamingMessage: '' })

          try {
            // 立即添加用户消息到 UI
            const userMessage: Message = {
              id: `temp-${Date.now()}`,
              conversationId,
              role: 'user',
              content,
              timestamp: Date.now()
            }

            set((state) => ({
              messages: {
                ...state.messages,
                [conversationId]: [...(state.messages[conversationId] || []), userMessage]
              }
            }))

            // 调用后端 API（后端会通过 Tauri Events 发送流式响应）
            await chatService.sendMessage(conversationId, content)

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
