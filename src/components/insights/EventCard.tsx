import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import type { Locale } from 'date-fns'
import { formatDistanceToNow } from 'date-fns'
import type { InsightEvent } from '@/lib/services/insights'
import { PhotoGrid } from '@/components/activity/PhotoGrid'
import { Trash2 } from 'lucide-react'

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

export function EventCard({ event, locale, onDelete }: EventCardProps) {
  const { t } = useTranslation()

  const handleDelete = () => {
    if (onDelete) {
      onDelete(event.id)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-1">
            <CardTitle className="text-lg">{event.title || event.description || t('insights.untitledEvent')}</CardTitle>
            <CardDescription>{formatRelative(event.timestamp, locale)}</CardDescription>
          </div>
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
