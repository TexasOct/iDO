import { TimelineDay } from '@/lib/types/activity'
import { ActivityItem } from './ActivityItem'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'
import { useEffect, useRef, useState, useMemo, ReactNode } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { CalendarDays, Clock, Timer, Zap, BarChart3, Grid3x3, ListTree } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

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

  // 为图表准备数据 - 按小时聚合活动数量
  const chartData = useMemo(() => {
    const hourMap = new Map<number, number>()
    day.activities.forEach((activity) => {
      const hour = new Date(activity.startTime).getHours()
      hourMap.set(hour, (hourMap.get(hour) || 0) + 1)
    })

    // 生成完整的24小时数据
    const data = []
    for (let hour = 0; hour < 24; hour++) {
      data.push({
        hour: `${hour.toString().padStart(2, '0')}:00`,
        count: hourMap.get(hour) || 0
      })
    }
    return data.filter((d) => d.count > 0) // 只显示有活动的小时
  }, [day.activities])

  // 活动分组统计
  const activityStats = useMemo(() => {
    const totalDuration = day.activities.reduce((sum, a) => sum + (a.endTime - a.startTime), 0)
    const avgDuration = day.activities.length > 0 ? totalDuration / day.activities.length : 0

    return {
      total: day.activities.length,
      totalDuration: Math.round(totalDuration / 60000), // 转换为分钟
      avgDuration: Math.round(avgDuration / 60000),
      withEvents: day.activities.filter((a) => a.eventSummaries?.length > 0).length
    }
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
      <div className="border-primary/15 bg-card/80 relative mb-8 overflow-hidden rounded-3xl border shadow-xl">
        <div className="from-primary/10 via-background/60 to-background pointer-events-none absolute inset-0 bg-linear-to-br opacity-80" />
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
                    className="bg-background/80 border-border/40 flex flex-col rounded-2xl border p-4 shadow-sm">
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

          {/* 工作内容进展 */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold tracking-widest text-emerald-600 uppercase dark:text-emerald-400">
              <ListTree className="h-4 w-4" />
              <span>{t('activity.sections.workProgress')}</span>
            </div>
            <div className="border-border/40 bg-background/70 space-y-2 rounded-2xl border p-4">
              <div className="flex items-start gap-2">
                <span className="mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                <div className="min-w-0 flex-1 text-sm">
                  <span className="text-foreground font-semibold">{t('activity.sections.weekProgress')}:</span>
                  <span className="text-muted-foreground ml-1">
                    {t('activity.sections.weekProgressDesc', {
                      count: actualDayCount,
                      minutes: totalDurationMinutes
                    })}
                  </span>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                <div className="min-w-0 flex-1 text-sm">
                  <span className="text-foreground font-semibold">{t('activity.sections.followUp')}:</span>
                  <span className="text-muted-foreground ml-1">{t('activity.sections.followUpDesc')}</span>
                </div>
              </div>
            </div>
          </section>

          {/* 界面可见活动进展 */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold tracking-widest text-purple-600 uppercase dark:text-purple-400">
              <Grid3x3 className="h-4 w-4" />
              <span>{t('activity.sections.uiProgress')}</span>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="border-border/40 bg-background/70 rounded-2xl border p-4">
                <div className="text-muted-foreground mb-1 text-xs tracking-widest uppercase">
                  {t('activity.sections.directView')}
                </div>
                <div className="text-primary text-2xl font-bold">{activityStats.total}</div>
                <div className="text-muted-foreground mt-1 text-xs">{t('activity.sections.activities')}</div>
              </div>
              <div className="border-border/40 bg-background/70 rounded-2xl border p-4">
                <div className="text-muted-foreground mb-1 text-xs tracking-widest uppercase">
                  {t('activity.sections.mergeOptimize')}
                </div>
                <div className="text-primary text-2xl font-bold">{activityStats.withEvents}</div>
                <div className="text-muted-foreground mt-1 text-xs">{t('activity.sections.withEvents')}</div>
              </div>
              <div className="border-border/40 bg-background/70 rounded-2xl border p-4">
                <div className="text-muted-foreground mb-1 text-xs tracking-widest uppercase">
                  {t('activity.sections.timeCompare')}
                </div>
                <div className="text-primary text-2xl font-bold">{activityStats.avgDuration}</div>
                <div className="text-muted-foreground mt-1 text-xs">{t('activity.sections.avgMinutes')}</div>
              </div>
            </div>
          </section>

          {/* 预期可见活动对比 */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold tracking-widest text-orange-600 uppercase dark:text-orange-400">
              <Grid3x3 className="h-4 w-4" />
              <span>{t('activity.sections.expectedView')}</span>
            </div>
            <div className="border-border/40 bg-background/70 overflow-hidden rounded-2xl border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-border/40 border-b">
                  <tr>
                    <th className="text-foreground px-4 py-3 text-left font-semibold">
                      {t('activity.sections.tableItem')}
                    </th>
                    <th className="text-foreground px-4 py-3 text-left font-semibold">
                      {t('activity.sections.tableBaseline')}
                    </th>
                    <th className="text-foreground px-4 py-3 text-left font-semibold">
                      {t('activity.sections.tableInterface')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-border/20 border-b">
                    <td className="text-muted-foreground px-4 py-3">{t('activity.sections.tableActivities')}</td>
                    <td className="text-foreground px-4 py-3 font-medium">{t('activity.sections.tableInitial')}</td>
                    <td className="text-foreground px-4 py-3 font-medium">{actualDayCount}</td>
                  </tr>
                  <tr className="border-border/20 border-b">
                    <td className="text-muted-foreground px-4 py-3">Todo</td>
                    <td className="text-foreground px-4 py-3 font-medium">{t('activity.sections.tableDate')}</td>
                    <td className="text-foreground px-4 py-3 font-medium">{t('activity.sections.tableMerge')}</td>
                  </tr>
                  <tr>
                    <td className="text-muted-foreground px-4 py-3">{t('activity.sections.tableDetailView')}</td>
                    <td className="text-foreground px-4 py-3 font-medium">{t('activity.sections.tableExpanded')}</td>
                    <td className="text-foreground px-4 py-3 font-medium">{t('activity.sections.tableExpanded')}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* 活动分布图表 */}
          {chartData.length > 0 && (
            <section className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold tracking-widest text-blue-600 uppercase dark:text-blue-400">
                <BarChart3 className="h-4 w-4" />
                <span>{t('activity.sections.distributionChart')}</span>
              </div>
              <div className="border-border/40 bg-background/70 overflow-hidden rounded-2xl border p-6">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border/20" />
                    <XAxis dataKey="hour" className="text-muted-foreground text-xs" />
                    <YAxis className="text-muted-foreground text-xs" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="count" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
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
              <div className="text-muted-foreground border-border/40 rounded-2xl border border-dashed py-8 text-center text-sm">
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
    <div className="bg-background/70 border-border/40 flex items-center gap-2 rounded-2xl border px-3 py-2 text-xs leading-tight shadow-sm">
      <span className="text-primary">{icon}</span>
      <div>
        <div className="text-muted-foreground tracking-widest uppercase">{label}</div>
        <div className="text-foreground text-sm font-semibold">{value}</div>
      </div>
    </div>
  )
}
