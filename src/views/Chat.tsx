/**
 * Chat 页面
 * 对话界面，支持流式输出
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

// 稳定的空数组引用
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

  // 当前会话的 UI 状态（基于数据推导）
  const sending = currentConversationId ? sendingConversationIds.has(currentConversationId) : false
  const streamingMessage = currentConversationId ? streamingMessages[currentConversationId] || '' : ''
  const isStreaming = !!streamingMessage // 有流式内容即表示正在流式输出

  // 使用 useMemo 确保引用稳定
  const messages = useMemo(() => {
    if (!currentConversationId) return EMPTY_ARRAY
    return allMessages[currentConversationId] || EMPTY_ARRAY
  }, [currentConversationId, allMessages])

  const currentConversation = useMemo(
    () => conversations.find((item) => item.id === currentConversationId) ?? null,
    [conversations, currentConversationId]
  )
  const conversationTitle = currentConversation?.title?.trim() || DEFAULT_CHAT_TITLE

  // 同步对话的模型选择
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

  // 监听流式消息
  useChatStream(currentConversationId)

  // 禁用后端流式状态轮询 - 前端已通过 Tauri Events 实时监听，后端轮询会导致状态冲突
  // useStreamingStatus(true)

  // 处理数据并发送到聊天 - 使用 useCallback 确保引用稳定
  const processDataToChat = useCallback(
    async ({ title, message, type, images }: { title: string; message: string; type: string; images?: string[] }) => {
      console.log(`[Chat] 开始处理${type}数据:`, { title, message, images })
      try {
        // 直接从 store 获取方法
        const createConv = useChatStore.getState().createConversation
        const setCurrentConv = useChatStore.getState().setCurrentConversation
        const setPendingMsg = useChatStore.getState().setPendingMessage
        const setPendingImgs = useChatStore.getState().setPendingImages

        console.log(`[Chat] 准备创建对话:`, title)
        // 创建新对话
        const conversation = await createConv(title)
        console.log(`[Chat] 对话创建成功:`, conversation.id)

        setCurrentConv(conversation.id)
        console.log(`[Chat] 设置当前对话ID:`, conversation.id)

        // 设置待发送消息和图片
        setPendingMsg(message)
        if (images && images.length > 0) {
          setPendingImgs(images)
          console.log(`[Chat] 设置待发送图片:`, images)
        }
        console.log(`[Chat] 设置待发送消息:`, message)

        console.log(`[Chat] ✅ 已创建新对话并设置${type}消息:`, conversation.id)
      } catch (error) {
        console.error(`[Chat] ❌ 处理${type}数据失败:`, error)
      }
    },
    []
  )

  // 监听来自各个模块的事件 - 将 processDataToChat 添加到依赖数组
  useEffect(() => {
    console.log('[Chat] 🚀 初始化事件监听器')

    // 待办列表事件
    const todoHandler = (data: any) => {
      console.log('[Chat] ✅ 收到待办执行事件:', data)
      processDataToChat({
        title: data.title || '新对话',
        message: `请帮我完成以下任务：\n\n标题：${data.title}\n\n${data.description || ''}`,
        type: 'todo'
      })
    }

    // 活动记录事件
    const activityHandler = (data: any) => {
      console.log('[Chat] ✅ 收到活动记录事件:', data)
      const screenshotsText = data.screenshots?.length
        ? `\n\n相关截图：${data.screenshots.length} 张（暂不自动添加）`
        : ''
      processDataToChat({
        title: data.title || '活动记录',
        message: `请帮我分析以下活动记录：\n\n标题：${data.title}\n\n${data.description || ''}${screenshotsText}`,
        type: 'activity',
        images: [] // ❌ 暂不传递图片
      })
    }

    // 最近事件事件
    const eventHandler = (data: any) => {
      console.log('[Chat] ✅ 收到最近事件:', data)
      const screenshotsText = data.screenshots?.length
        ? `\n\n相关截图：${data.screenshots.length} 张（暂不自动添加）`
        : ''
      processDataToChat({
        title: data.summary || '事件记录',
        message: `请帮我分析以下事件：\n\n${data.summary}\n\n${data.description || ''}${screenshotsText}`,
        type: 'event',
        images: [] // ❌ 暂不传递图片
      })
    }

    // 知识整理事件
    const knowledgeHandler = (data: any) => {
      console.log('[Chat] ✅ 收到知识整理:', data)
      processDataToChat({
        title: data.title || '知识整理',
        message: `请帮我整理以下知识：\n\n${data.description}`,
        type: 'knowledge'
      })
    }

    // 注册事件监听器
    eventBus.on('todo:execute-in-chat', todoHandler)
    eventBus.on('activity:send-to-chat', activityHandler)
    eventBus.on('event:send-to-chat', eventHandler)
    eventBus.on('knowledge:send-to-chat', knowledgeHandler)

    console.log('[Chat] 事件监听器注册完成')

    // 清理订阅
    return () => {
      console.log('[Chat] 清理事件监听器')
      eventBus.off('todo:execute-in-chat', todoHandler)
      eventBus.off('activity:send-to-chat', activityHandler)
      eventBus.off('event:send-to-chat', eventHandler)
      eventBus.off('knowledge:send-to-chat', knowledgeHandler)
    }
  }, [processDataToChat])

  // 处理从活动页面跳转过来的情况
  useEffect(() => {
    const activityId = searchParams.get('activityId')
    if (activityId) {
      console.debug('[Chat] 从活动页面跳转，关联活动ID:', activityId)
      setPendingActivityId(activityId)

      // 自动创建一个新对话并关联活动
      const createNewConversationWithActivity = async () => {
        try {
          const conversation = await createConversation(DEFAULT_CHAT_TITLE, [activityId])
          setCurrentConversation(conversation.id)
          console.debug('[Chat] 已创建新对话并关联活动:', conversation.id)
        } catch (error) {
          console.error('[Chat] 创建对话失败:', error)
        }
      }

      createNewConversationWithActivity()

      // 清除 URL 参数，避免刷新时重复处理
      setSearchParams({})
    }
  }, [searchParams, setPendingActivityId, setSearchParams, createConversation, setCurrentConversation])

  // 初始化：加载对话列表
  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  // Tauri 拖拽事件监听 - 使用 onDragDropEvent() API
  useEffect(() => {
    let unlistenDragDrop: (() => void) | null = null
    let dragOverTimeout: ReturnType<typeof setTimeout> | null = null

    const setupDragDropListener = async () => {
      try {
        const webview = getCurrentWebview()

        unlistenDragDrop = await webview.onDragDropEvent((event: any) => {
          // 从 event.payload 中获取拖拽事件数据
          const dragDropPayload = event.payload
          console.log('[Chat] Drag drop event:', dragDropPayload.type, dragDropPayload)

          if (dragDropPayload.type === 'enter') {
            // 用户正在拖拽文件进入
            console.log('[Chat] Drag enter - paths:', dragDropPayload.paths)
            setIsDraggingFiles(true)

            // 清除之前的超时
            if (dragOverTimeout) {
              clearTimeout(dragOverTimeout)
            }
          } else if (dragDropPayload.type === 'over') {
            // 用户在拖拽时移动 - 保持高亮状态
            console.log('[Chat] Drag over')
            setIsDraggingFiles(true)
          } else if (dragDropPayload.type === 'drop') {
            // 用户释放了拖拽的文件
            console.log('[Chat] Drag drop - paths:', dragDropPayload.paths)
            setIsDraggingFiles(false)

            if (dragOverTimeout) {
              clearTimeout(dragOverTimeout)
              dragOverTimeout = null
            }

            const filePaths = dragDropPayload.paths || []

            // 过滤出图片文件
            const imageFilePaths = filePaths.filter((filePath: string) => {
              const ext = filePath.split('.').pop()?.toLowerCase()
              return ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext || '')
            })

            // 将文件路径添加到待发送图片中
            // 后端会在发送消息时读取和处理这些文件
            if (imageFilePaths.length > 0) {
              console.log('[Chat] Adding image file paths:', imageFilePaths.length)
              const currentPendingImages = useChatStore.getState().pendingImages || []
              useChatStore.setState({
                pendingImages: [...currentPendingImages, ...imageFilePaths]
              })

              // 如果没有当前对话，创建新对话
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
            // 用户将文件拖出窗口
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

  // 当切换对话时，加载消息
  useEffect(() => {
    if (currentConversationId) {
      fetchMessages(currentConversationId)
    }
  }, [currentConversationId, fetchMessages])

  // 处理新建对话
  const handleNewConversation = async () => {
    try {
      // 如果有待关联的活动，创建时关联
      const relatedActivityIds = pendingActivityId ? [pendingActivityId] : undefined
      const conversation = await createConversation(DEFAULT_CHAT_TITLE, relatedActivityIds, selectedModelId)
      setCurrentConversation(conversation.id)

      // 清除待关联的活动ID
      if (pendingActivityId) {
        setPendingActivityId(null)
      }
    } catch (error) {
      console.error('创建对话失败:', error)
    }
  }

  // 处理模型变更
  const handleModelChange = (modelId: string) => {
    setSelectedModelId(modelId)
  }

  // 处理发送消息
  const handleSendMessage = async (content: string, images?: string[]) => {
    if (!currentConversationId) {
      // 如果没有当前对话，先创建一个
      // 如果有待关联的活动，创建时关联
      const relatedActivityIds = pendingActivityId ? [pendingActivityId] : undefined
      const conversation = await createConversation(DEFAULT_CHAT_TITLE, relatedActivityIds, selectedModelId)
      setCurrentConversation(conversation.id)
      await sendMessage(conversation.id, content, images, selectedModelId)

      // 清除待关联的活动ID
      if (pendingActivityId) {
        setPendingActivityId(null)
      }
    } else {
      await sendMessage(currentConversationId, content, images, selectedModelId)
    }
  }

  // 处理删除对话
  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await deleteConversation(conversationId)
    } catch (error) {
      console.error('删除对话失败:', error)
    }
  }

  // 处理终止流式输出
  const handleCancelStream = async () => {
    if (!currentConversationId || isCancelling) return

    setIsCancelling(true)
    try {
      await apiClient.cancelStream({ conversationId: currentConversationId })
      console.log('✅ 已请求取消流式输出')

      // 清除本地流式状态
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
      console.error('取消流式输出失败:', error)
    } finally {
      setIsCancelling(false)
    }
  }

  // 处理重试失败的消息
  const handleRetry = async (conversationId: string, messageId: string) => {
    const conversationMessages = allMessages[conversationId] || []

    // 找到当前错误消息
    const errorMessage = conversationMessages.find((msg) => msg.id === messageId)
    if (!errorMessage || !errorMessage.error) {
      console.error('未找到错误消息')
      return
    }

    // 找到对应的用户消息（应该在错误消息之前）
    const errorIndex = conversationMessages.findIndex((msg) => msg.id === messageId)
    const lastUserMessage = [...conversationMessages.slice(0, errorIndex)].reverse().find((msg) => msg.role === 'user')

    if (!lastUserMessage) {
      console.error('未找到对应的用户消息')
      return
    }

    // 删除错误消息
    const filteredMessages = conversationMessages.filter((msg) => msg.id !== messageId)

    // 更新 store 中的消息列表
    useChatStore.setState((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: filteredMessages
      }
    }))

    // 设置发送状态
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
      // 直接调用后端 API，不添加新的用户消息
      await apiClient.sendMessage({
        conversationId,
        content: lastUserMessage.content,
        images: lastUserMessage.images
      })
    } catch (error) {
      console.error('重试发送失败:', error)
      // 移除发送状态
      useChatStore.setState((state) => {
        const newSendingIds = new Set(state.sendingConversationIds)
        newSendingIds.delete(conversationId)
        return { sendingConversationIds: newSendingIds }
      })
    }
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(200px,260px)_minmax(0,1fr)] items-stretch">
      {/* 左侧：对话列表 */}
      <ConversationList
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelect={setCurrentConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />

      {/* 右侧：消息区域 */}
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        {/* 拖拽文件的高亮覆盖层 */}
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
            {/* Header - 全宽 */}
            <div className="border-border/80 flex items-center justify-between border-b px-4 py-4 sm:px-6">
              <div>
                <h1 className="text-lg leading-tight font-semibold">{conversationTitle}</h1>
                {currentConversation?.metadata?.generatedTitleSource === 'auto' && (
                  <p className="text-muted-foreground mt-1 text-xs">{t('chat.autoSummary')}</p>
                )}
              </div>
            </div>

            {/* 消息列表 - 居中限宽 */}
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

            {/* 活动上下文 - 居中限宽 */}
            {pendingActivityId && !loadingMessages && (
              <div className="flex justify-center border-t">
                <div className="w-full max-w-4xl px-4 py-3 sm:px-6">
                  <ActivityContext activityId={pendingActivityId} onDismiss={() => setPendingActivityId(null)} />
                </div>
              </div>
            )}

            {/* 输入框 - 居中限宽 */}
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
