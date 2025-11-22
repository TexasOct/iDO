import { TimelineDay } from '@/lib/types/activity'
import { ActivityItem } from './ActivityItem'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'
import { useEffect, useRef, useState, useMemo, ReactNode } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { CalendarDays, Clock, Timer, Zap } from 'lucide-react'

interface TimelineDayItemProps {
  day: TimelineDay
  isNew?: boolean
}

export function TimelineDayItem({ day, isNew: isNewProp = false }: TimelineDayItemProps) {
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement>(null)
  const [showHighlights, setShowHighlights] = useState(true)

  // 修复时区问题：day.date 是 YYYY-MM-DD 格式，直接拆分而不通过 Date 构造函数以避免 UTC 转换
  const [year, month, dayOfMonth] = day.date.split('-').map(Number)
  const date = new Date(year, month - 1, dayOfMonth)
  const formattedDate = format(date, 'yyyy年MM月dd日 EEEE', { locale: zhCN })

  // 直接从 store 中选择该日期的计数值，这样当这个值变化时能立即触发重新渲染
  const actualDayCount = useActivityStore((state) => state.dateCountMap[day.date] || 0)

  // 检查是否有新活动（如果日期块本身没被标记为新，检查活动中是否有新的）
  const isNew = isNewProp || day.activities.some((activity) => (activity as any).isNew)

  const totalActivities = day.activities.length
  const totalDurationMinutes = useMemo(() => {
    if (day.activities.length === 0) return 0
    return Math.max(
      0,
      Math.round(
        day.activities.reduce((sum, activity) => {
          const duration = Math.max(activity.endTime - activity.startTime, 0)
          return sum + duration
        }, 0) / 60000
      )
    )
  }, [day.activities])

  const timeRange = useMemo(() => {
    if (!day.activities.length) return '--'
    const earliest = day.activities.reduce(
      (min, activity) => Math.min(min, activity.startTime),
      day.activities[0].startTime
    )
    const latest = day.activities.reduce((max, activity) => Math.max(max, activity.endTime), day.activities[0].endTime)
    return `${format(new Date(earliest), 'HH:mm')} - ${format(new Date(latest), 'HH:mm')}`
  }, [day.activities])

  const highlightActivities = useMemo(() => {
    return day.activities.slice(0, 3)
  }, [day.activities])

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
    <div
      ref={containerRef}
      className={`relative ${isNew ? 'animate-in fade-in slide-in-from-top-4 duration-500' : ''}`}>
      <div className="border-border bg-card relative mb-8 overflow-hidden rounded-lg border shadow-sm">
        <div className="relative z-10 space-y-6 p-6">
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-muted-foreground text-xs tracking-[0.3em] uppercase">{t('activity.timeline')}</p>
              <h2 className="text-foreground text-2xl font-semibold">{formattedDate}</h2>
              <p className="text-muted-foreground text-sm">
                {t('activity.overview.title')}: {actualDayCount}
                {t('activity.activitiesCount')}
              </p>
            </div>
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <StatChip
                icon={<CalendarDays className="h-4 w-4" />}
                label={t('activity.stats.activities')}
                value={`${totalActivities}`}
              />
              <StatChip
                icon={<Timer className="h-4 w-4" />}
                label={t('activity.stats.focusMinutes')}
                value={`${totalDurationMinutes} ${t('activity.overview.minutes')}`}
              />
              <StatChip icon={<Clock className="h-4 w-4" />} label={t('activity.focusRange')} value={timeRange} />
            </div>
          </header>

          {showHighlights && highlightActivities.length > 0 && (
            <section className="space-y-3">
              <div className="text-muted-foreground flex items-center justify-between text-sm font-semibold tracking-widest uppercase">
                <span>{t('activity.highlights')}</span>
                <button
                  type="button"
                  className="text-primary hover:text-primary/80 text-xs font-medium transition"
                  onClick={() => setShowHighlights(false)}>
                  {t('common.collapse')}
                </button>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                {highlightActivities.map((activity) => (
                  <div
                    key={activity.id}
                    className="border-border bg-background flex flex-col rounded-lg border p-4 shadow-sm">
                    <span className="text-foreground line-clamp-1 text-sm font-semibold">
                      {activity.title || t('activity.untitled')}
                    </span>
                    <span className="text-muted-foreground text-xs">
                      {format(new Date(activity.startTime), 'HH:mm')} - {format(new Date(activity.endTime), 'HH:mm')}
                    </span>
                    {activity.description && (
                      <p className="text-muted-foreground mt-2 line-clamp-3 text-xs leading-relaxed">
                        {activity.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {!showHighlights && highlightActivities.length > 0 && (
            <button
              type="button"
              className="text-primary text-xs font-medium underline-offset-2 transition hover:underline"
              onClick={() => setShowHighlights(true)}>
              {t('activity.highlights')}
            </button>
          )}

          {/* 活动详细列表 */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Zap className="text-primary h-4 w-4" />
              <span>{t('activity.timelineDetails')}</span>
            </div>
            {day.activities.length > 0 ? (
              <div className="space-y-3">
                {day.activities.map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
              </div>
            ) : (
              <div className="border-border text-muted-foreground rounded-lg border border-dashed py-8 text-center text-sm">
                {t('activity.noData')}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

function StatChip({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="border-border bg-card flex items-center gap-2 rounded-lg border px-3 py-2 text-xs leading-tight shadow-sm">
      <span className="text-primary">{icon}</span>
      <div>
        <div className="text-muted-foreground tracking-widest uppercase">{label}</div>
        <div className="text-foreground text-sm font-semibold">{value}</div>
      </div>
    </div>
  )
}
