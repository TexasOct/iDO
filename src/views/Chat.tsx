/**
 * Chat 页面
 * 对话界面，支持流式输出
 */

import { useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router'
import { useChatStore, DEFAULT_CHAT_TITLE } from '@/lib/stores/chat'
import { useChatStream } from '@/hooks/useChatStream'
import { ConversationList } from '@/components/chat/ConversationList'
import { MessageList } from '@/components/chat/MessageList'
import { MessageInput } from '@/components/chat/MessageInput'
import { ActivityContext } from '@/components/chat/ActivityContext'

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
    <div className="flex h-full min-h-0 items-stretch">
      {/* 左侧：对话列表 */}
      <ConversationList
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelect={setCurrentConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />

      {/* 右侧：消息区域 */}
      <div className="flex min-h-0 flex-1 flex-col">
        {currentConversationId ? (
          <>
            <div className="border-border/80 flex items-center justify-between border-b px-6 py-4">
              <div>
                <h1 className="text-lg leading-tight font-semibold">{conversationTitle}</h1>
                {currentConversation?.metadata?.generatedTitleSource === 'auto' && (
                  <p className="text-muted-foreground mt-1 text-xs">{t('chat.autoSummary')}</p>
                )}
              </div>
            </div>

            {/* 消息列表 */}
            <div className="min-h-0 flex-1 overflow-y-auto">
              <MessageList
                messages={messages}
                streamingMessage={streamingMessage}
                isStreaming={isStreaming}
                loading={loading}
              />
            </div>

            {/* 活动上下文 - 在输入框上方 */}
            {pendingActivityId && (
              <div className="border-t px-6 py-3">
                <ActivityContext activityId={pendingActivityId} onDismiss={() => setPendingActivityId(null)} />
              </div>
            )}

            {/* 输入框 */}
            <MessageInput
              onSend={handleSendMessage}
              disabled={sending || isStreaming}
              placeholder={isStreaming ? t('chat.aiResponding') : t('chat.inputPlaceholder')}
              initialMessage={pendingMessage || undefined}
            />
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
