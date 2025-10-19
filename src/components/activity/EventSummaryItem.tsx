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
  const { expandedItems, toggleExpanded } = useActivityStore()
  const isExpanded = expandedItems.has(summary.id)

  const time = format(new Date(summary.timestamp), 'HH:mm:ss')

  return (
    <div className="border-l-2 border-muted pl-4">
      <button onClick={() => toggleExpanded(summary.id)} className="flex items-start gap-2 text-left w-full group py-2">
        <div className="mt-0.5">
          {isExpanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <FileText className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="font-medium text-sm group-hover:text-primary transition-colors">{summary.title}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span>{time}</span>
            <span>·</span>
            <span>{summary.events.length}{t('activity.eventsCount')}</span>
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
