import { Event } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { ChevronDown, ChevronRight, Zap } from 'lucide-react'
import { format } from 'date-fns'
import { RecordItem } from './RecordItem'
import { useTranslation } from 'react-i18next'

interface EventItemProps {
  event: Event
}

export function EventItem({ event }: EventItemProps) {
  const { t } = useTranslation()
  const { expandedItems, toggleExpanded } = useActivityStore()
  const isExpanded = expandedItems.has(event.id)

  const time = format(new Date(event.timestamp), 'HH:mm:ss')

  return (
    <div className="bg-muted/30 rounded-lg p-3">
      <button onClick={() => toggleExpanded(event.id)} className="flex items-start gap-2 text-left w-full group">
        <div className="mt-0.5">
          {isExpanded ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Zap className="h-3 w-3 text-muted-foreground" />
            <span className="text-sm font-medium group-hover:text-primary transition-colors">{event.type}</span>
          </div>
          {event.summary && <p className="text-xs text-muted-foreground mt-1">{event.summary}</p>}
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span>{time}</span>
            <span>·</span>
            <span>{event.records.length}{t('activity.recordsCount')}</span>
          </div>
        </div>
      </button>

      {isExpanded && (
        <div className="mt-3 space-y-1 pl-5">
          {event.records.map((record) => (
            <RecordItem key={record.id} record={record} />
          ))}
        </div>
      )}
    </div>
  )
}
