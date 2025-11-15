/**
 * 消息项组件
 * 使用 shadcn/ui AI Response 组件进行渲染
 */

import { useDeferredValue } from 'react'
import { cn } from '@/lib/utils'
import type { Message } from '@/lib/types/chat'
import { Bot, User } from 'lucide-react'
import { Response } from '@/components/ui/ai-response'
import { useTranslation } from 'react-i18next'

interface MessageItemProps {
  message: Message
  isStreaming?: boolean
}

export function MessageItem({ message, isStreaming }: MessageItemProps) {
  const { t } = useTranslation()
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const deferredContent = useDeferredValue(message.content)
  const assistantContent = isStreaming ? deferredContent : message.content

  if (isSystem) {
    return <div className="text-muted-foreground mx-4 my-2 rounded-lg px-4 py-2 text-sm">{message.content}</div>
  }

  return (
    <div className={cn('flex max-w-full gap-3 px-4 py-3', 'bg-background', isStreaming && 'animate-pulse')}>
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
        )}>
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className="flex-1 space-y-1 overflow-hidden">
        <p className="text-sm leading-none font-medium">
          {isUser ? t('chat.you') : t('chat.aiAssistant')}
          {isStreaming && <span className="text-muted-foreground ml-2 text-xs">{t('chat.typing')}</span>}
        </p>

        {/* 显示图片（如果有） */}
        {message.images && message.images.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {message.images.map((image, index) => (
              <img
                key={index}
                src={image}
                alt={`Image ${index + 1}`}
                className="max-h-64 max-w-sm rounded-lg border object-contain"
              />
            ))}
          </div>
        )}

        {/* 显示文本内容 */}
        {message.content && (
          <div className="text-foreground prose dark:prose-invert max-w-none text-base [&_.code-block-container]:m-0! [&_p:has(>.code-block-container)]:m-0! [&_p:has(>.code-block-container)]:p-0!">
            {isUser ? (
              // 用户消息：保持原样显示
              <div className="warp-break-words whitespace-pre-wrap">{message.content}</div>
            ) : (
              // AI 消息：使用 shadcn Response 组件渲染
              <>
                <Response parseIncompleteMarkdown={isStreaming}>{assistantContent}</Response>
                {isStreaming && <span className="bg-primary ml-1 inline-block h-4 w-2 animate-pulse" />}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
