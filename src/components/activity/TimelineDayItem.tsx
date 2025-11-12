import { TimelineDay } from '@/lib/types/activity'
import { ActivityItem } from './ActivityItem'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'
import { useEffect, useRef } from 'react'
import { useActivityStore } from '@/lib/stores/activity'

interface TimelineDayItemProps {
  day: TimelineDay
  isNew?: boolean
}

export function TimelineDayItem({ day, isNew: isNewProp = false }: TimelineDayItemProps) {
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement>(null)

  // 修复时区问题：day.date 是 YYYY-MM-DD 格式，直接拆分而不通过 Date 构造函数以避免 UTC 转换
  const [year, month, dayOfMonth] = day.date.split('-').map(Number)
  const date = new Date(year, month - 1, dayOfMonth)
  const formattedDate = format(date, 'yyyy年MM月dd日 EEEE', { locale: zhCN })

  // 直接从 store 中选择该日期的计数值，这样当这个值变化时能立即触发重新渲染
  const actualDayCount = useActivityStore((state) => state.dateCountMap[day.date] || 0)

  // 检查是否有新活动（如果日期块本身没被标记为新，检查活动中是否有新的）
  const isNew = isNewProp || day.activities.some((activity) => (activity as any).isNew)

  // 新日期块进入时的动画（整个日期块都是新的情况）
  useEffect(() => {
    if (isNewProp && containerRef.current) {
      const timer = setTimeout(() => {
        if (containerRef.current) {
          containerRef.current.classList.remove('animate-in')
        }
      }, 600)
      return () => clearTimeout(timer)
    }
  }, [isNewProp])

  return (
    <div ref={containerRef} className={isNew ? 'animate-in fade-in slide-in-from-top-4 duration-500' : ''}>
      <div className="space-y-4">
        <div
          className={`bg-background/95 supports-backdrop-filter:bg-background/60 sticky top-0 z-10 border-b pb-2 backdrop-blur transition-colors ${isNew ? 'bg-primary/10' : ''}`}>
          <h2 className={`text-lg font-semibold ${isNew ? 'text-primary' : ''}`}>{formattedDate}</h2>
          <p className="text-muted-foreground text-sm">
            {actualDayCount}
            {t('activity.activitiesCount')}
          </p>
        </div>

        <div className="space-y-3 pl-4">
          {day.activities.map((activity) => (
            <ActivityItem key={activity.id} activity={activity} />
          ))}
        </div>
      </div>
    </div>
  )
}
