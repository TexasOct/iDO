import { TimelineDay } from '@/lib/types/activity'
import { TimelineDayItem } from './TimelineDayItem'

interface ActivityTimelineProps {
  data: (TimelineDay & { isNew?: boolean })[]
}

/**
 * Simplified ActivityTimeline component
 * Responsible for rendering timeline data; virtual scrolling is managed by the Activity View
 */
export function ActivityTimeline({ data }: ActivityTimelineProps) {
  if (data.length === 0) {
    return null
  }

  return (
    <div className="relative z-10">
      {data.map((day) => (
        <TimelineDayItem key={day.date} day={day} isNew={day.isNew} />
      ))}
    </div>
  )
}
