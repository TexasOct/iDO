import { EventSummary } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { ChevronDown, ChevronRight, FileText } from 'lucide-react'
import { format } from 'date-fns'
import { EventItem } from './EventItem'
import { useTranslation } from 'react-i18next'

interface EventSummaryItemProps {
  summary: EventSummary
}

export function EventSummaryItem({ summary }: EventSummaryItemProps) {
  const { t } = useTranslation()
  // 分别订阅各个字段，避免选择器返回新对象
  const expandedItems = useActivityStore((state) => state.expandedItems)
  const toggleExpanded = useActivityStore((state) => state.toggleExpanded)
  const isExpanded = expandedItems.has(summary.id)

  const time = format(new Date(summary.timestamp), 'HH:mm:ss')

  return (
    <div className="border-muted border-l-2 pl-4">
      <button onClick={() => toggleExpanded(summary.id)} className="group flex w-full items-start gap-2 py-2 text-left">
        <div className="mt-0.5">
          {isExpanded ? (
            <ChevronDown className="text-muted-foreground h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="text-muted-foreground h-3.5 w-3.5" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <FileText className="text-muted-foreground h-3.5 w-3.5" />
            <span className="group-hover:text-primary text-sm font-medium transition-colors">{summary.title}</span>
          </div>
          <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
            <span>{time}</span>
            <span>·</span>
            <span>
              {summary.events.length}
              {t('activity.eventsCount')}
            </span>
          </div>
        </div>
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-2">
          {summary.events.map((event) => (
            <EventItem key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}
