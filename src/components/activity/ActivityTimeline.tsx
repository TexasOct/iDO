import { TimelineDay } from '@/lib/types/activity'
import { TimelineDayItem } from './TimelineDayItem'

interface ActivityTimelineProps {
  data: TimelineDay[]
}

export function ActivityTimeline({ data }: ActivityTimelineProps) {
  if (data.length === 0) {
    return null
  }

  return (
    <div className="space-y-6">
      {data.map((day) => (
        <TimelineDayItem key={day.date} day={day} />
      ))}
    </div>
  )
}
