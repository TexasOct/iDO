import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import type { Locale } from 'date-fns'
import { formatDistanceToNow } from 'date-fns'
import type { InsightEvent } from '@/lib/services/insights'
import { PhotoGrid } from '@/components/activity/PhotoGrid'
import { Trash2, MessageSquare } from 'lucide-react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { emitEventToChat } from '@/lib/events/eventBus'

interface EventCardProps {
  event: InsightEvent
  locale: Locale
  onDelete?: (eventId: string) => void
}

const formatRelative = (timestamp?: string, locale?: Locale) => {
  if (!timestamp) return ''
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return ''
  try {
    return formatDistanceToNow(parsed, { addSuffix: true, locale })
  } catch (error) {
    console.error('Failed to format timestamp', error)
    return ''
  }
}

const toNumericTimestamp = (timestamp?: string | number) => {
  if (typeof timestamp === 'number' && Number.isFinite(timestamp)) {
    return timestamp
  }
  if (typeof timestamp === 'string') {
    const parsed = Date.parse(timestamp)
    if (!Number.isNaN(parsed)) {
      return parsed
    }
  }
  return Date.now()
}

export function EventCard({ event, locale, onDelete }: EventCardProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const handleDelete = () => {
    if (onDelete) {
      onDelete(event.id)
    }
  }

  const handleSendToChat = () => {
    toast.success('正在跳转到对话...')

    // 先跳转到 Chat
    navigate('/chat')

    // 延迟 200ms 发布事件，确保 Chat 组件已挂载并注册了事件监听器
    setTimeout(() => {
      emitEventToChat({
        eventId: event.id,
        summary: event.title || event.description || t('insights.untitledEvent'),
        description: event.description,
        screenshots: [], // ❌ 暂不传递图片，避免 HTTP 431 错误
        keywords: event.keywords || [],
        timestamp: toNumericTimestamp(event.timestamp)
      })
      console.log('[EventCard] 延迟200ms发布事件（暂不传图片）')
    }, 200)
  }

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-1">
            <CardTitle className="text-lg">{event.title || event.description || t('insights.untitledEvent')}</CardTitle>
            <CardDescription>{formatRelative(event.timestamp, locale)}</CardDescription>
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleSendToChat}
              className="text-muted-foreground hover:text-foreground"
              title="发送到对话（文字自动预填充，图片需手动添加）">
              <MessageSquare className="h-4 w-4" />
            </Button>
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleDelete}
                className="text-muted-foreground hover:text-destructive">
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {event.description && <p className="text-muted-foreground text-sm leading-6">{event.description}</p>}
        {event.keywords && event.keywords.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {event.keywords.slice(0, 6).map((keyword) => (
              <Badge key={keyword} variant="secondary">
                {keyword}
              </Badge>
            ))}
            {event.keywords.length > 6 && (
              <span className="text-muted-foreground text-xs">+{event.keywords.length - 6}</span>
            )}
          </div>
        )}
        {event.screenshots.length > 0 && (
          <PhotoGrid images={event.screenshots} title={event.title || event.description || 'event'} />
        )}
      </CardContent>
    </Card>
  )
}
