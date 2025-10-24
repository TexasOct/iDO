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
  // 分别订阅各个字段，避免选择器返回新对象
  const expandedItems = useActivityStore((state) => state.expandedItems)
  const toggleExpanded = useActivityStore((state) => state.toggleExpanded)
  const isExpanded = expandedItems.has(event.id)

  const time = format(new Date(event.timestamp), 'HH:mm:ss')

  return (
    <div className="bg-muted/30 rounded-lg p-3">
      <button onClick={() => toggleExpanded(event.id)} className="group flex w-full items-start gap-2 text-left">
        <div className="mt-0.5">
          {isExpanded ? (
            <ChevronDown className="text-muted-foreground h-3 w-3" />
          ) : (
            <ChevronRight className="text-muted-foreground h-3 w-3" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Zap className="text-muted-foreground h-3 w-3" />
            <span className="group-hover:text-primary text-sm font-medium transition-colors">{event.type}</span>
          </div>
          <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
            <span>{time}</span>
            <span>·</span>
            <span>
              {event.records.length}
              {t('activity.recordsCount')}
            </span>
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
