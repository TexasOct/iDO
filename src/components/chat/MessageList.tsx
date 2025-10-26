/**
 * 消息列表组件
 */

import { useEffect, useRef } from 'react'
import { MessageItem } from './MessageItem'
import type { Message } from '@/lib/types/chat'
import { Loader2 } from 'lucide-react'

interface MessageListProps {
  messages: Message[]
  streamingMessage?: string
  isStreaming?: boolean
  loading?: boolean
}

export function MessageList({ messages, streamingMessage, isStreaming, loading }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const { scrollTop, scrollHeight, clientHeight } = container
    const distanceToBottom = scrollHeight - clientHeight - scrollTop
    const shouldStickToBottom = isStreaming || distanceToBottom < 120

    if (!shouldStickToBottom) return

    const behavior: ScrollBehavior = isStreaming ? 'auto' : 'smooth'

    requestAnimationFrame(() => {
      container.scrollTo({ top: container.scrollHeight, behavior })
    })
  }, [messages, streamingMessage, isStreaming])

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-muted-foreground text-center">
          <p className="text-lg font-medium">开始新对话</p>
          <p className="mt-2 text-sm">输入消息开始与 AI 助手对话</p>
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto">
      <div className="space-y-0">
        {messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))}

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
    </div>
  )
}
