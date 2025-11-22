import { TimelineDay } from '@/lib/types/activity'
import { TimelineDayItem } from './TimelineDayItem'

interface ActivityTimelineProps {
  data: (TimelineDay & { isNew?: boolean })[]
}

/**
 * 简化的 ActivityTimeline 组件
 * 负责渲染时间线数据，虚拟滚动由 Activity View 管理
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
