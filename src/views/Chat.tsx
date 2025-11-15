/**
 * Chat 页面
 * 对话界面，支持流式输出
 */

import { useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'
import { useChatStore, DEFAULT_CHAT_TITLE } from '@/lib/stores/chat'
import { useChatStream } from '@/hooks/useChatStream'
import { ConversationList } from '@/components/chat/ConversationList'
import { MessageList } from '@/components/chat/MessageList'
import { MessageInput } from '@/components/chat/MessageInput'
import { ActivityContext } from '@/components/chat/ActivityContext'
import { eventBus } from '@/lib/events/eventBus'

// 稳定的空数组引用
const EMPTY_ARRAY: any[] = []

export default function Chat() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()

  // Store state
  const conversations = useChatStore((state) => state.conversations)
  const currentConversationId = useChatStore((state) => state.currentConversationId)
  const allMessages = useChatStore((state) => state.messages)
  const streamingMessage = useChatStore((state) => state.streamingMessage)
  const isStreaming = useChatStore((state) => state.isStreaming)
  const loading = useChatStore((state) => state.loading)
  const sending = useChatStore((state) => state.sending)
  const pendingActivityId = useChatStore((state) => state.pendingActivityId)
  const pendingMessage = useChatStore((state) => state.pendingMessage)

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
      const conversation = await createConversation(DEFAULT_CHAT_TITLE, relatedActivityIds)
      setCurrentConversation(conversation.id)

      // 清除待关联的活动ID
      if (pendingActivityId) {
        setPendingActivityId(null)
      }
    } catch (error) {
      console.error('创建对话失败:', error)
    }
  }

  // 处理发送消息
  const handleSendMessage = async (content: string, images?: string[]) => {
    if (!currentConversationId) {
      // 如果没有当前对话，先创建一个
      // 如果有待关联的活动，创建时关联
      const relatedActivityIds = pendingActivityId ? [pendingActivityId] : undefined
      const conversation = await createConversation(DEFAULT_CHAT_TITLE, relatedActivityIds)
      setCurrentConversation(conversation.id)
      await sendMessage(conversation.id, content, images)

      // 清除待关联的活动ID
      if (pendingActivityId) {
        setPendingActivityId(null)
      }
    } else {
      await sendMessage(currentConversationId, content, images)
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

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(200px,260px)_minmax(0,1fr)] items-stretch pt-3">
      {/* 左侧：对话列表 */}
      <ConversationList
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelect={setCurrentConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />

      {/* 右侧：消息区域 */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        {currentConversationId ? (
          <>
            <div className="border-border/80 flex items-center justify-between border-b px-4 py-4 sm:px-6">
              <div>
                <h1 className="text-lg leading-tight font-semibold">{conversationTitle}</h1>
                {currentConversation?.metadata?.generatedTitleSource === 'auto' && (
                  <p className="text-muted-foreground mt-1 text-xs">{t('chat.autoSummary')}</p>
                )}
              </div>
            </div>

            {/* 消息列表 */}
            <div className="min-h-0 min-w-0 flex-1 overflow-y-auto px-4 sm:px-6">
              <MessageList
                messages={messages}
                streamingMessage={streamingMessage}
                isStreaming={isStreaming}
                loading={loading}
              />
            </div>

            {/* 活动上下文 - 在输入框上方 */}
            {pendingActivityId && (
              <div className="border-t px-4 py-3 sm:px-6">
                <ActivityContext activityId={pendingActivityId} onDismiss={() => setPendingActivityId(null)} />
              </div>
            )}

            {/* 输入框 */}
            <div className="border-t px-4 py-3 sm:px-6">
              <MessageInput
                onSend={handleSendMessage}
                disabled={sending || isStreaming}
                placeholder={isStreaming ? t('chat.aiResponding') : t('chat.inputPlaceholder')}
                initialMessage={pendingMessage || undefined}
              />
            </div>
          </>
        ) : (
          <div className="text-muted-foreground flex flex-1 items-center justify-center">
            <div className="text-center">
              <p className="text-lg font-medium">{t('chat.selectOrCreate')}</p>
              <p className="mt-2 text-sm">{t('chat.startChatting')}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
