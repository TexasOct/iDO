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
        <button onClick={() => toggleExpanded(activity.id)} className="group flex w-full items-start gap-2 text-left">
          <div className="mt-0.5">
            {isExpanded ? (
              <ChevronDown className="text-muted-foreground h-4 w-4" />
            ) : (
              <ChevronRight className="text-muted-foreground h-4 w-4" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle className="group-hover:text-primary text-base transition-colors">{activity.name}</CardTitle>
            <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
              <Clock className="h-3 w-3" />
              <span>{time}</span>
              <span>·</span>
              <span>
                {activity.eventSummaries.length}
                {t('activity.eventSummariesCount')}
              </span>
            </div>
          </div>
        </button>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-2 pt-0">
          {activity.eventSummaries.map((summary) => (
            <EventSummaryItem key={summary.id} summary={summary} />
          ))}
        </CardContent>
      )}
    </Card>
  )
}
