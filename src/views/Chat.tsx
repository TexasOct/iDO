/**
 * Chat view
 * Conversation interface with streaming output support
 */

import { useEffect, useMemo, useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'
import { getCurrentWebview } from '@tauri-apps/api/webview'
import { useChatStore, DEFAULT_CHAT_TITLE } from '@/lib/stores/chat'
import { useChatStream } from '@/hooks/useChatStream'
import { ConversationList } from '@/components/chat/ConversationList'
import { MessageList } from '@/components/chat/MessageList'
import { MessageInput } from '@/components/chat/MessageInput'
import { ActivityContext } from '@/components/chat/ActivityContext'
import { eventBus } from '@/lib/events/eventBus'
import * as apiClient from '@/lib/client/apiClient'

// Stable empty array reference
const EMPTY_ARRAY: any[] = []

export default function Chat() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [isCancelling, setIsCancelling] = useState(false)
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null)
  const [isDraggingFiles, setIsDraggingFiles] = useState(false)

  // Store state
  const conversations = useChatStore((state) => state.conversations)
  const currentConversationId = useChatStore((state) => state.currentConversationId)
  const allMessages = useChatStore((state) => state.messages)
  const streamingMessages = useChatStore((state) => state.streamingMessages)
  const loadingMessages = useChatStore((state) => state.loadingMessages)
  const sendingConversationIds = useChatStore((state) => state.sendingConversationIds)
  const pendingActivityId = useChatStore((state) => state.pendingActivityId)
  const pendingMessage = useChatStore((state) => state.pendingMessage)

  // Derived UI state for current conversation
  const sending = currentConversationId ? sendingConversationIds.has(currentConversationId) : false
  const streamingMessage = currentConversationId ? streamingMessages[currentConversationId] || '' : ''
  const isStreaming = !!streamingMessage // Streaming output is active whenever content exists

  // Use useMemo to keep references stable
  const messages = useMemo(() => {
    if (!currentConversationId) return EMPTY_ARRAY
    return allMessages[currentConversationId] || EMPTY_ARRAY
  }, [currentConversationId, allMessages])

  const currentConversation = useMemo(
    () => conversations.find((item) => item.id === currentConversationId) ?? null,
    [conversations, currentConversationId]
  )
  const conversationTitle = currentConversation?.title?.trim() || DEFAULT_CHAT_TITLE

  // Sync model selection with the current conversation
  useEffect(() => {
    if (currentConversation?.modelId) {
      setSelectedModelId(currentConversation.modelId)
    } else {
      setSelectedModelId(null)
    }
  }, [currentConversation])

  // Store actions
  const fetchConversations = useChatStore((state) => state.fetchConversations)
  const fetchMessages = useChatStore((state) => state.fetchMessages)
  const setCurrentConversation = useChatStore((state) => state.setCurrentConversation)
  const createConversation = useChatStore((state) => state.createConversation)
  const sendMessage = useChatStore((state) => state.sendMessage)
  const deleteConversation = useChatStore((state) => state.deleteConversation)
  const setPendingActivityId = useChatStore((state) => state.setPendingActivityId)

  // Subscribe to streaming messages
  useChatStream(currentConversationId)

  // Disable backend streaming status polling since the frontend already listens through Tauri events
  // useStreamingStatus(true)

  // Process incoming data and forward it to chat (useCallback keeps reference stable)
  const processDataToChat = useCallback(
    async ({ title, message, type, images }: { title: string; message: string; type: string; images?: string[] }) => {
      console.log(`[Chat] Start processing ${type} data:`, { title, message, images })
      try {
        // Get store actions directly
        const createConv = useChatStore.getState().createConversation
        const setCurrentConv = useChatStore.getState().setCurrentConversation
        const setPendingMsg = useChatStore.getState().setPendingMessage
        const setPendingImgs = useChatStore.getState().setPendingImages

        console.log('[Chat] Preparing to create conversation:', title)
        // Create a new conversation
        const conversation = await createConv(title)
        console.log('[Chat] Conversation created:', conversation.id)

        setCurrentConv(conversation.id)
        console.log('[Chat] Set current conversation ID:', conversation.id)

        // Populate pending message and images
        setPendingMsg(message)
        if (images && images.length > 0) {
          setPendingImgs(images)
          console.log('[Chat] Set pending images:', images)
        }
        console.log('[Chat] Set pending message:', message)

        console.log(`[Chat] ✅ Created conversation and populated ${type} payload:`, conversation.id)
      } catch (error) {
        console.error(`[Chat] ❌ Failed to process ${type} data:`, error)
      }
    },
    []
  )

  // Listen to events from other modules (processDataToChat must stay in deps)
  useEffect(() => {
    console.log('[Chat] 🚀 Initializing event listeners')

    // Todo events
    const todoHandler = (data: any) => {
      console.log('[Chat] ✅ Received todo execution event:', data)
      processDataToChat({
        title: data.title || 'New Conversation',
        message: `Help me complete the following task:\n\nTitle: ${data.title}\n\n${data.description || ''}`,
        type: 'todo'
      })
    }

    // Activity record events
    const activityHandler = (data: any) => {
      console.log('[Chat] ✅ Received activity event:', data)
      const screenshotsText = data.screenshots?.length
        ? `\n\nScreenshots: ${data.screenshots.length} (not automatically attached)`
        : ''
      processDataToChat({
        title: data.title || 'Activity record',
        message: `Please analyze the following activity record:\n\nTitle: ${data.title}\n\n${data.description || ''}${screenshotsText}`,
        type: 'activity',
        images: [] // Screenshots are not forwarded yet
      })
    }

    // Recent event timeline data
    const eventHandler = (data: any) => {
      console.log('[Chat] ✅ Received recent event:', data)
      const screenshotsText = data.screenshots?.length
        ? `\n\nScreenshots: ${data.screenshots.length} (not automatically attached)`
        : ''
      processDataToChat({
        title: data.summary || 'Event record',
        message: `Please analyze the following event:\n\n${data.summary}\n\n${data.description || ''}${screenshotsText}`,
        type: 'event',
        images: [] // Screenshots are not forwarded yet
      })
    }

    // Knowledge curation events
    const knowledgeHandler = (data: any) => {
      console.log('[Chat] ✅ Received knowledge entry:', data)
      processDataToChat({
        title: data.title || 'Knowledge entry',
        message: `Please organize the following knowledge:\n\n${data.description}`,
        type: 'knowledge'
      })
    }

    // Register listeners
    eventBus.on('todo:execute-in-chat', todoHandler)
    eventBus.on('activity:send-to-chat', activityHandler)
    eventBus.on('event:send-to-chat', eventHandler)
    eventBus.on('knowledge:send-to-chat', knowledgeHandler)

    console.log('[Chat] Event listeners registered')

    // Cleanup subscriptions
    return () => {
      console.log('[Chat] Cleaning up event listeners')
      eventBus.off('todo:execute-in-chat', todoHandler)
      eventBus.off('activity:send-to-chat', activityHandler)
      eventBus.off('event:send-to-chat', eventHandler)
      eventBus.off('knowledge:send-to-chat', knowledgeHandler)
    }
  }, [processDataToChat])

  // Handle navigation initiated from the Activity page
  useEffect(() => {
    const activityId = searchParams.get('activityId')
    if (activityId) {
      console.debug('[Chat] Navigated from activity view, linking ID:', activityId)
      setPendingActivityId(activityId)

      // Automatically create a new conversation and associate the activity
      const createNewConversationWithActivity = async () => {
        try {
          const conversation = await createConversation(DEFAULT_CHAT_TITLE, [activityId])
          setCurrentConversation(conversation.id)
          console.debug('[Chat] Created conversation and linked activity:', conversation.id)
        } catch (error) {
          console.error('[Chat] Failed to create conversation:', error)
        }
      }

      createNewConversationWithActivity()

      // Clear URL params so refresh does not re-trigger the logic
      setSearchParams({})
    }
  }, [searchParams, setPendingActivityId, setSearchParams, createConversation, setCurrentConversation])

  // Initial load: fetch conversation list
  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  // Tauri drag-and-drop listener using onDragDropEvent()
  useEffect(() => {
    let unlistenDragDrop: (() => void) | null = null
    let dragOverTimeout: ReturnType<typeof setTimeout> | null = null
    let lastDropSignature: string | null = null
    let lastDropTimestamp = 0
    const DUPLICATE_DROP_COOLDOWN_MS = 300

    const setupDragDropListener = async () => {
      try {
        const webview = getCurrentWebview()

        unlistenDragDrop = await webview.onDragDropEvent((event: any) => {
          // Extract drag/drop event data from payload
          const dragDropPayload = event.payload
          console.log('[Chat] Drag drop event:', dragDropPayload.type, dragDropPayload)

          if (dragDropPayload.type === 'enter') {
            // User is dragging files into the window
            console.log('[Chat] Drag enter - paths:', dragDropPayload.paths)
            setIsDraggingFiles(true)

            // Clear existing timeout
            if (dragOverTimeout) {
              clearTimeout(dragOverTimeout)
            }
          } else if (dragDropPayload.type === 'over') {
            // User is moving files while dragging - keep highlight visible
            console.log('[Chat] Drag over')
            setIsDraggingFiles(true)
          } else if (dragDropPayload.type === 'drop') {
            // User released files
            console.log('[Chat] Drag drop - paths:', dragDropPayload.paths)
            setIsDraggingFiles(false)

            if (dragOverTimeout) {
              clearTimeout(dragOverTimeout)
              dragOverTimeout = null
            }

            const filePaths = dragDropPayload.paths || []

            // Filter out image files
            const imageFilePaths = filePaths.filter((filePath: string) => {
              const ext = filePath.split('.').pop()?.toLowerCase()
              return ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext || '')
            })

            // Add file paths to pending images
            // Backend reads these files when sending the message
            if (imageFilePaths.length > 0) {
              // Deduplicate repeated drop events triggered by Tauri during the same drop
              const dropSignature = imageFilePaths.join('|')
              const now = Date.now()
              const isDuplicate =
                dropSignature === lastDropSignature && now - lastDropTimestamp < DUPLICATE_DROP_COOLDOWN_MS

              if (isDuplicate) {
                console.log('[Chat] Duplicate drop event ignored')
                return
              }

              lastDropSignature = dropSignature
              lastDropTimestamp = now

              console.log('[Chat] Adding image file paths:', imageFilePaths.length)
              const currentPendingImages = useChatStore.getState().pendingImages || []
              useChatStore.setState({
                pendingImages: [...currentPendingImages, ...imageFilePaths]
              })

              // Create a conversation if none is active
              if (!currentConversationId) {
                console.log('[Chat] Creating new conversation for dropped images')
                const relatedActivityIds = pendingActivityId ? [pendingActivityId] : undefined
                createConversation(DEFAULT_CHAT_TITLE, relatedActivityIds, selectedModelId).then((conversation) => {
                  console.log('[Chat] New conversation created:', conversation.id)
                  setCurrentConversation(conversation.id)
                })
              }
            }
          } else if (dragDropPayload.type === 'leave') {
            // User dragged files out of the window
            console.log('[Chat] Drag leave')
            setIsDraggingFiles(false)

            if (dragOverTimeout) {
              clearTimeout(dragOverTimeout)
              dragOverTimeout = null
            }
          }
        })
      } catch (error) {
        console.error('[Chat] Error setting up Tauri drag-drop listener:', error)
      }
    }

    setupDragDropListener()

    return () => {
      if (dragOverTimeout) {
        clearTimeout(dragOverTimeout)
      }
      if (unlistenDragDrop) {
        unlistenDragDrop()
      }
    }
  }, [currentConversationId, pendingActivityId, selectedModelId, createConversation, setCurrentConversation])

  // Load messages when switching conversations
  useEffect(() => {
    if (currentConversationId) {
      fetchMessages(currentConversationId)
    }
  }, [currentConversationId, fetchMessages])

  // Handle creating a new conversation
  const handleNewConversation = async () => {
    try {
      // Associate pending activity if available
      const relatedActivityIds = pendingActivityId ? [pendingActivityId] : undefined
      const conversation = await createConversation(DEFAULT_CHAT_TITLE, relatedActivityIds, selectedModelId)
      setCurrentConversation(conversation.id)

      // Clear pending activity ID
      if (pendingActivityId) {
        setPendingActivityId(null)
      }
    } catch (error) {
      console.error('Failed to create conversation:', error)
    }
  }

  // Handle model change
  const handleModelChange = (modelId: string) => {
    setSelectedModelId(modelId)
  }

  // Handle sending messages
  const handleSendMessage = async (content: string, images?: string[]) => {
    if (!currentConversationId) {
      // Create a conversation first when none is active
      // Associate pending activity if available
      const relatedActivityIds = pendingActivityId ? [pendingActivityId] : undefined
      const conversation = await createConversation(DEFAULT_CHAT_TITLE, relatedActivityIds, selectedModelId)
      setCurrentConversation(conversation.id)
      await sendMessage(conversation.id, content, images, selectedModelId)

      // Clear pending activity ID
      if (pendingActivityId) {
        setPendingActivityId(null)
      }
    } else {
      await sendMessage(currentConversationId, content, images, selectedModelId)
    }
  }

  // Handle deleting a conversation
  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await deleteConversation(conversationId)
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }

  // Handle canceling streaming responses
  const handleCancelStream = async () => {
    if (!currentConversationId || isCancelling) return

    setIsCancelling(true)
    try {
      await apiClient.cancelStream({ conversationId: currentConversationId })
      console.log('✅ Requested to cancel streaming output')

      // Clear the local streaming state
      useChatStore.setState((state) => {
        const newStreamingMessages = { ...state.streamingMessages }
        delete newStreamingMessages[currentConversationId]

        const newSendingIds = new Set(state.sendingConversationIds)
        newSendingIds.delete(currentConversationId)

        return {
          streamingMessages: newStreamingMessages,
          sendingConversationIds: newSendingIds
        }
      })
    } catch (error) {
      console.error('Failed to cancel streaming output:', error)
    } finally {
      setIsCancelling(false)
    }
  }

  // Handle retrying failed assistant responses
  const handleRetry = async (conversationId: string, messageId: string) => {
    const conversationMessages = allMessages[conversationId] || []

    // Find the error message
    const errorMessage = conversationMessages.find((msg) => msg.id === messageId)
    if (!errorMessage || !errorMessage.error) {
      console.error('Error message not found')
      return
    }

    // Find the user message that preceded the error
    const errorIndex = conversationMessages.findIndex((msg) => msg.id === messageId)
    const lastUserMessage = [...conversationMessages.slice(0, errorIndex)].reverse().find((msg) => msg.role === 'user')

    if (!lastUserMessage) {
      console.error('Corresponding user message not found')
      return
    }

    // Remove the error message
    const filteredMessages = conversationMessages.filter((msg) => msg.id !== messageId)

    // Update the store with filtered messages
    useChatStore.setState((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: filteredMessages
      }
    }))

    // Mark the conversation as sending again
    useChatStore.setState((state) => {
      const newSendingIds = new Set(state.sendingConversationIds)
      newSendingIds.add(conversationId)
      return {
        sendingConversationIds: newSendingIds,
        streamingMessages: {
          ...state.streamingMessages,
          [conversationId]: ''
        }
      }
    })

    try {
      // Call the backend directly without inserting another user message
      await apiClient.sendMessage({
        conversationId,
        content: lastUserMessage.content,
        images: lastUserMessage.images
      })
    } catch (error) {
      console.error('Retry send failed:', error)
      // Remove sending state again
      useChatStore.setState((state) => {
        const newSendingIds = new Set(state.sendingConversationIds)
        newSendingIds.delete(conversationId)
        return { sendingConversationIds: newSendingIds }
      })
    }
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(200px,260px)_minmax(0,1fr)] items-stretch">
      {/* Left column: conversation list */}
      <ConversationList
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelect={setCurrentConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />

      {/* Right column: message area */}
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        {/* Drag-and-drop highlight overlay */}
        {isDraggingFiles && (
          <div className="border-primary bg-primary/5 pointer-events-none absolute inset-0 z-50 flex items-center justify-center rounded-lg border-2 border-dashed backdrop-blur-sm">
            <div className="text-center">
              <svg
                className="text-primary mx-auto mb-3 h-12 w-12"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <p className="text-primary font-semibold">{t('chat.dropImagesToAdd') || 'Drop images here'}</p>
              <p className="text-muted-foreground text-sm">{t('chat.supportedFormats') || 'PNG, JPG, GIF'}</p>
            </div>
          </div>
        )}

        {currentConversationId ? (
          <>
            {/* Header - full width */}
            <div className="border-border/80 flex items-center justify-between border-b px-4 py-4 sm:px-6">
              <div>
                <h1 className="text-lg leading-tight font-semibold">{conversationTitle}</h1>
                {currentConversation?.metadata?.generatedTitleSource === 'auto' && (
                  <p className="text-muted-foreground mt-1 text-xs">{t('chat.autoSummary')}</p>
                )}
              </div>
            </div>

            {/* Message list - centered with max width */}
            <div className="flex min-h-0 flex-1 justify-center">
              <div className="flex w-full max-w-4xl flex-col overflow-hidden px-8">
                <MessageList
                  messages={messages}
                  streamingMessage={streamingMessage}
                  isStreaming={isStreaming}
                  loading={loadingMessages}
                  sending={sending}
                  onRetry={handleRetry}
                />
              </div>
            </div>

            {/* Activity context - centered with max width */}
            {pendingActivityId && !loadingMessages && (
              <div className="flex justify-center border-t">
                <div className="w-full max-w-4xl px-4 py-3 sm:px-6">
                  <ActivityContext activityId={pendingActivityId} onDismiss={() => setPendingActivityId(null)} />
                </div>
              </div>
            )}

            {/* Input area - centered with max width */}
            <div className="flex justify-center bg-transparent">
              <div className="w-full max-w-4xl px-4 pb-3 sm:px-6">
                <MessageInput
                  onSend={handleSendMessage}
                  onCancel={handleCancelStream}
                  disabled={sending || loadingMessages}
                  isStreaming={sending || isStreaming}
                  isCancelling={isCancelling}
                  placeholder={
                    loadingMessages
                      ? t('chat.loadingMessages')
                      : isStreaming
                        ? t('chat.aiResponding')
                        : sending
                          ? t('chat.thinking')
                          : t('chat.inputPlaceholder')
                  }
                  initialMessage={pendingMessage || undefined}
                  conversationId={currentConversationId}
                  selectedModelId={selectedModelId}
                  onModelChange={handleModelChange}
                />
              </div>
            </div>
          </>
        ) : (
          <div className="text-muted-foreground flex flex-1 items-center justify-center">
            <div className="text-center">
              <p className="text-lg font-medium">{t('chat.selectOrCreate')}</p>
              <p className="mt-2 text-sm">{t('chat.startChatting')}</p>
              <button
                onClick={handleNewConversation}
                className="bg-primary text-primary-foreground hover:bg-primary/90 mt-4 rounded-lg px-4 py-2 text-sm font-medium transition-colors">
                {t('chat.newConversation')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
