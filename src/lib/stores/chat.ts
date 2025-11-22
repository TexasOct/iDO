/**
 * Chat Zustand Store
 * Manage conversation and message state
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Conversation, Message } from '@/lib/types/chat'
import * as chatService from '@/lib/services/chat'

export const DEFAULT_CHAT_TITLE = 'New Conversation'
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
  // Data state
  conversations: Conversation[]
  messages: Record<string, Message[]> // conversationId -> messages
  currentConversationId: string | null
  streamingMessages: Record<string, string> // conversationId -> streaming message content (pushed via events)

  // Local UI state (supports simultaneous sending)
  sendingConversationIds: Set<string> // Conversations currently sending and awaiting backend response

  // Activity association context
  pendingActivityId: string | null // Activity ID pending association

  // Pending message and images
  pendingMessage: string | null // Message that prefills the input
  pendingImages: string[] // Images that prefills the input

  // Pending data from other modules
  pendingExternalData: any | null

  // Loading state
  loading: boolean
  loadingMessages: boolean // Loading flag for the current conversation

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

  // Streaming message handling
  appendStreamingChunk: (conversationId: string, chunk: string) => void
  setStreamingComplete: (conversationId: string, messageId?: string) => void
  resetStreaming: (conversationId: string) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => {
      // Each conversation keeps its own pending chunks and scheduler
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

          // Remove from the sending set when the first chunk arrives
          if (isFirstChunk && state.sendingConversationIds.has(conversationId)) {
            console.log(`[Chat] Received first stream chunk; remove from sending: ${conversationId}`)
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
        // Initial state
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

        // Set the current conversation
        setCurrentConversation: (conversationId) => {
          set({ currentConversationId: conversationId })
        },

        // Set the pending activity ID
        setPendingActivityId: (activityId) => {
          set({ pendingActivityId: activityId })
        },

        // Set the pending message
        setPendingMessage: (message) => {
          set({ pendingMessage: message })
        },

        // Set the pending images
        setPendingImages: (images) => {
          set({ pendingImages: images })
        },

        // Set the pending external data
        setPendingExternalData: (data) => {
          set({ pendingExternalData: data })
        },

        // Fetch the conversation list
        fetchConversations: async () => {
          set({ loading: true })
          try {
            const conversations = await chatService.getConversations({ limit: 50 })
            set({ conversations, loading: false })
          } catch (error) {
            console.error('Failed to fetch conversations:', error)
            set({ loading: false })
          }
        },

        refreshConversations: async () => {
          try {
            const conversations = await chatService.getConversations({ limit: 50 })
            set({ conversations })
          } catch (error) {
            console.error('Failed to refresh conversations:', error)
          }
        },

        // Fetch the message list
        fetchMessages: async (conversationId) => {
          set({ loadingMessages: true })
          try {
            const messages = await chatService.getMessages({
              conversationId,
              limit: 100
            })

            // Convert metadata.error into an error field
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
            console.error('Failed to fetch messages:', error)
            set({ loadingMessages: false })
          }
        },

        // Create a conversation
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
            console.error('Failed to create conversation:', error)
            set({ loading: false })
            throw error
          }
        },

        // Create conversation from activities
        createConversationFromActivities: async (activityIds) => {
          set({ loading: true })
          try {
            const result = await chatService.createConversationFromActivities(activityIds)

            // Refresh the conversation list
            await get().fetchConversations()

            // Set as the current conversation
            set({
              currentConversationId: result.conversationId,
              loading: false
            })

            // Load messages
            await get().fetchMessages(result.conversationId)

            return result.conversationId
          } catch (error) {
            console.error('Failed to create conversation from activities:', error)
            set({ loading: false })
            throw error
          }
        },

        // Send a message
        sendMessage: async (conversationId, content, images, modelId) => {
          console.log(`[Chat] Sending message; add to sending set: ${conversationId}`)
          set((state) => {
            const newSendingIds = new Set(state.sendingConversationIds)
            newSendingIds.add(conversationId)
            return {
              sendingConversationIds: newSendingIds,
              streamingMessages: {
                ...state.streamingMessages,
                [conversationId]: '' // Pre-clear the streaming buffer
              }
            }
          })

          try {
            // Immediately add the user message to the UI
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

            // Call the backend API (stream responses via Tauri events)
            await chatService.sendMessage(conversationId, content, images, modelId)
            // Note: localSendingConversationId is cleared when the first chunk arrives
          } catch (error) {
            console.error('Failed to send message:', error)

            // Append an error message to the UI
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

              // Remove this conversation from the sending set
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

        // Delete a conversation
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
            console.error('Failed to delete conversation:', error)
            set({ loading: false })
            throw error
          }
        },

        // Append a streaming chunk
        appendStreamingChunk: (conversationId, chunk) => {
          const currentChunks = pendingChunksMap.get(conversationId) || ''
          pendingChunksMap.set(conversationId, currentChunks + chunk)
          scheduleFlush(conversationId)
        },

        // Streaming message completed
        setStreamingComplete: async (conversationId, messageId) => {
          clearScheduledFlush(conversationId)

          // Refresh pending chunks for this conversation
          const pendingChunks = pendingChunksMap.get(conversationId) || ''
          if (pendingChunks) {
            flushPendingChunks(conversationId)
          }

          const { streamingMessages } = get()
          const streamingMessage = streamingMessages[conversationId] || ''

          // Save the streaming message into the message list
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

              // Remove this conversation from the sending set if it is still present
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
            // If no streaming data exists, refetch the message list
            await get().fetchMessages(conversationId)
            set((state) => {
              const newStreamingMessages = { ...state.streamingMessages }
              delete newStreamingMessages[conversationId]

              // Remove this conversation from the sending set if it is still present
              const newSendingIds = new Set(state.sendingConversationIds)
              newSendingIds.delete(conversationId)

              return {
                streamingMessages: newStreamingMessages,
                sendingConversationIds: newSendingIds
              }
            })
          }

          // Clear pending data for this conversation
          pendingChunksMap.delete(conversationId)

          await get().refreshConversations()
        },

        // Reset streaming state
        resetStreaming: (conversationId) => {
          clearScheduledFlush(conversationId)
          pendingChunksMap.delete(conversationId)

          set((state) => {
            const newStreamingMessages = { ...state.streamingMessages }
            delete newStreamingMessages[conversationId]

            return {
              streamingMessages: newStreamingMessages
              // streamingMessages alone signals streaming; nothing else to clear
            }
          })
        }
      }
    },
    {
      name: 'chat-storage',
      partialize: (state) => ({
        currentConversationId: state.currentConversationId
        // Do not persist conversations/messages; reload on startup
      })
    }
  )
)
