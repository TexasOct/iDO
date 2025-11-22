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
  onRetry?: (conversationId: string, messageId: string) => void
}

export function MessageList({ messages, streamingMessage, isStreaming, loading, sending, onRetry }: MessageListProps) {
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
        <MessageItem key={message.id} message={message} onRetry={onRetry} />
      ))}

      {/* AI 思考中 / 流式输出 */}
      {(sending || isStreaming) && (
        <MessageItem
          message={{
            id: 'streaming',
            conversationId: '',
            role: 'assistant',
            content: streamingMessage || '',
            timestamp: Date.now()
          }}
          isStreaming={isStreaming}
          isThinking={sending && !isStreaming}
        />
      )}
    </div>
  )
}
