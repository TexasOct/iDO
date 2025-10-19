import { Activity } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronDown, ChevronRight, Clock } from 'lucide-react'
import { format } from 'date-fns'
import { EventSummaryItem } from './EventSummaryItem'
import { useTranslation } from 'react-i18next'

interface ActivityItemProps {
  activity: Activity
}

export function ActivityItem({ activity }: ActivityItemProps) {
  const { t } = useTranslation()
  const { expandedItems, toggleExpanded } = useActivityStore()
  const isExpanded = expandedItems.has(activity.id)

  const time = format(new Date(activity.timestamp), 'HH:mm:ss')

  return (
    <Card>
      <CardHeader className="py-3">
        <button onClick={() => toggleExpanded(activity.id)} className="flex items-start gap-2 text-left w-full group">
          <div className="mt-0.5">
            {isExpanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
          </div>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base group-hover:text-primary transition-colors">{activity.name}</CardTitle>
            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{time}</span>
              <span>·</span>
              <span>{activity.eventSummaries.length}{t('activity.eventSummariesCount')}</span>
            </div>
          </div>
        </button>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0 space-y-2">
          {activity.eventSummaries.map((summary) => (
            <EventSummaryItem key={summary.id} summary={summary} />
          ))}
        </CardContent>
      )}
    </Card>
  )
}
