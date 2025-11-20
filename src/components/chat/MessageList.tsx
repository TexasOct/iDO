/**
 * 消息列表组件
 */

import { useEffect, useRef } from 'react'
import { MessageItem } from './MessageItem'
import type { Message } from '@/lib/types/chat'
import { Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface MessageListProps {
  messages: Message[]
  streamingMessage?: string
  isStreaming?: boolean
  loading?: boolean
  sending?: boolean
}

export function MessageList({ messages, streamingMessage, isStreaming, loading, sending }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const { t } = useTranslation()
  // 自动滚动到底部
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const { scrollTop, scrollHeight, clientHeight } = container
    const distanceToBottom = scrollHeight - clientHeight - scrollTop
    const shouldStickToBottom = isStreaming || sending || distanceToBottom < 120

    if (!shouldStickToBottom) return

    const behavior: ScrollBehavior = isStreaming || sending ? 'auto' : 'smooth'

    requestAnimationFrame(() => {
      container.scrollTo({ top: container.scrollHeight, behavior })
    })
  }, [messages, streamingMessage, isStreaming, sending])

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (messages.length === 0 && !isStreaming && !sending) {
    return (
      <div className="text-muted-foreground flex h-full flex-1 items-center justify-center">
        <div className="flex flex-col items-center justify-center text-center">
          <p className="text-lg font-medium">{t('chat.startChatting')}</p>
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="relative flex-1 overflow-y-auto pt-3">
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}

      {/* AI 思考中动画 - 在发送消息后、流式输出前显示 */}
      {sending && !streamingMessage && (
        <div className="max-w-full space-y-2 px-4 pb-6">
          {/* 头像和用户名 */}
          <div className="flex items-center gap-2">
            <div className="bg-secondary text-secondary-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
            <p className="text-sm leading-none font-medium">
              {t('chat.aiAssistant')}
              <span className="text-muted-foreground ml-2 text-xs">{t('chat.thinking')}</span>
            </p>
          </div>
          {/* 思考动画 */}
          <div className="ml-10 flex items-center gap-1">
            <div className="bg-foreground/40 h-2 w-2 animate-bounce rounded-full [animation-delay:-0.3s]"></div>
            <div className="bg-foreground/40 h-2 w-2 animate-bounce rounded-full [animation-delay:-0.15s]"></div>
            <div className="bg-foreground/40 h-2 w-2 animate-bounce rounded-full"></div>
          </div>
        </div>
      )}

      {/* 流式消息 */}
      {isStreaming && streamingMessage && (
        <MessageItem
          message={{
            id: 'streaming',
            conversationId: '',
            role: 'assistant',
            content: streamingMessage,
            timestamp: Date.now()
          }}
          isStreaming
        />
      )}
    </div>
  )
}
