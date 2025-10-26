/**
 * Chat 页面
 * 对话界面，支持流式输出
 */

import { useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useChatStore, DEFAULT_CHAT_TITLE } from '@/lib/stores/chat'
import { useChatStream } from '@/hooks/use-chat-stream'
import { ConversationList } from '@/components/chat/ConversationList'
import { MessageList } from '@/components/chat/MessageList'
import { MessageInput } from '@/components/chat/MessageInput'

// 稳定的空数组引用
const EMPTY_ARRAY: any[] = []

export default function Chat() {
  const { t } = useTranslation()
  // Store state
  const conversations = useChatStore((state) => state.conversations)
  const currentConversationId = useChatStore((state) => state.currentConversationId)
  const allMessages = useChatStore((state) => state.messages)
  const streamingMessage = useChatStore((state) => state.streamingMessage)
  const isStreaming = useChatStore((state) => state.isStreaming)
  const loading = useChatStore((state) => state.loading)
  const sending = useChatStore((state) => state.sending)

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

  // 监听流式消息
  useChatStream(currentConversationId)

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
      const conversation = await createConversation(DEFAULT_CHAT_TITLE)
      setCurrentConversation(conversation.id)
    } catch (error) {
      console.error('创建对话失败:', error)
    }
  }

  // 处理发送消息
  const handleSendMessage = async (content: string) => {
    if (!currentConversationId) {
      // 如果没有当前对话，先创建一个
      const conversation = await createConversation(DEFAULT_CHAT_TITLE)
      setCurrentConversation(conversation.id)
      await sendMessage(conversation.id, content)
    } else {
      await sendMessage(currentConversationId, content)
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
    <div className="flex h-full">
      {/* 左侧：对话列表 */}
      <ConversationList
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelect={setCurrentConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />

      {/* 右侧：消息区域 */}
      <div className="flex flex-1 flex-col">
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
            <MessageList
              messages={messages}
              streamingMessage={streamingMessage}
              isStreaming={isStreaming}
              loading={loading}
            />

            {/* 输入框 */}
            <MessageInput
              onSend={handleSendMessage}
              disabled={sending || isStreaming}
              placeholder={isStreaming ? 'AI 正在回复中...' : '输入消息... (Cmd/Ctrl + Enter 发送)'}
            />
          </>
        ) : (
          <div className="text-muted-foreground flex flex-1 items-center justify-center">
            <div className="text-center">
              <p className="text-lg font-medium">选择对话或创建新对话</p>
              <p className="mt-2 text-sm">开始与 AI 助手交流</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
