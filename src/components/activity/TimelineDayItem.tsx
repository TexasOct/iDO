import { TimelineDay } from '@/lib/types/activity'
import { ActivityItem } from './ActivityItem'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'

interface TimelineDayItemProps {
  day: TimelineDay
}

export function TimelineDayItem({ day }: TimelineDayItemProps) {
  const { t } = useTranslation()
  const date = new Date(day.date)
  const formattedDate = format(date, 'yyyy年MM月dd日 EEEE', { locale: zhCN })

  return (
    <div className="space-y-4">
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b pb-2">
        <h2 className="text-lg font-semibold">{formattedDate}</h2>
        <p className="text-sm text-muted-foreground">{day.activities.length}{t('activity.activitiesCount')}</p>
      </div>

      <div className="space-y-3 pl-4">
        {day.activities.map((activity) => (
          <ActivityItem key={activity.id} activity={activity} />
        ))}
      </div>
    </div>
  )
}
