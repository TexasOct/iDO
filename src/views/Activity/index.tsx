import { useEffect, useMemo, useState, useRef } from 'react'
import { useSearchParams } from 'react-router'
import { format, formatDistanceToNow } from 'date-fns'
import type { Locale } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ActivitySummary, ActivityEventDetail, fetchActivities, fetchEventsByIds } from '@/lib/services/activityNew'
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll'
import { toast } from 'sonner'

interface GroupedActivities {
  date: string
  activities: (ActivitySummary & { startTimestamp: number })[]
}

const localeMap: Record<string, Locale> = {
  zh: zhCN,
  'zh-CN': zhCN,
  en: enUS,
  'en-US': enUS
}

const ACTIVITY_PAGE_SIZE = 20
const MAX_WINDOW_SIZE = 100 // 滑动窗口最大容量
const toDataUrl = (value: string) => (value.startsWith('data:') ? value : `data:image/jpeg;base64,${value}`)

export default function ActivityView() {
  const { t, i18n } = useTranslation()
  const [searchParams] = useSearchParams()
  const [activities, setActivities] = useState<(ActivitySummary & { startTimestamp: number })[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [topOffset, setTopOffset] = useState(0)
  const [bottomOffset, setBottomOffset] = useState(0)
  const [hasMoreTop, setHasMoreTop] = useState(false)
  const [hasMoreBottom, setHasMoreBottom] = useState(true)
  const isLoadingRef = useRef(false)
  const itemRefs = useRef(new Map<string, HTMLDivElement>())
  const focusedId = searchParams.get('focus') || ''

  const locale = useMemo(() => localeMap[i18n.language] ?? enUS, [i18n.language])

  // 加载初始数据
  const loadInitialActivities = async () => {
    if (isLoadingRef.current) return
    isLoadingRef.current = true
    setLoading(true)
    setError(null)

    try {
      const result = await fetchActivities(ACTIVITY_PAGE_SIZE, 0)
      const normalized = result.map((activity) => ({
        ...activity,
        startTimestamp: Date.parse(activity.startTime || activity.createdAt || '') || Date.now()
      }))

      setActivities(normalized)
      setTopOffset(0)
      setBottomOffset(normalized.length)
      setHasMoreTop(false)
      setHasMoreBottom(normalized.length === ACTIVITY_PAGE_SIZE)
    } catch (err) {
      console.error('[ActivityView] Failed to fetch initial activities', err)
      const errorMessage = (err as Error).message
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
      isLoadingRef.current = false
    }
  }

  // 处理滚动加载
  const handleLoadMore = async (direction: 'top' | 'bottom') => {
    if (isLoadingRef.current) return

    if (direction === 'top' && !hasMoreTop) return
    if (direction === 'bottom' && !hasMoreBottom) return

    isLoadingRef.current = true
    console.log(`[ActivityView] Loading more from ${direction}`)

    try {
      const offset = direction === 'top' ? topOffset : bottomOffset
      const result = await fetchActivities(ACTIVITY_PAGE_SIZE, offset)

      if (result.length === 0) {
        if (direction === 'top') {
          setHasMoreTop(false)
        } else {
          setHasMoreBottom(false)
        }
        return
      }

      const normalized = result.map((activity) => ({
        ...activity,
        startTimestamp: Date.parse(activity.startTime || activity.createdAt || '') || Date.now()
      }))

      setActivities((prev) => {
        let newActivities: (ActivitySummary & { startTimestamp: number })[]

        if (direction === 'top') {
          newActivities = [...normalized, ...prev]
          setTopOffset(offset + normalized.length)
          setHasMoreTop(normalized.length === ACTIVITY_PAGE_SIZE)
        } else {
          newActivities = [...prev, ...normalized]
          setBottomOffset(offset + normalized.length)
          setHasMoreBottom(normalized.length === ACTIVITY_PAGE_SIZE)
        }

        // 滑动窗口管理
        if (newActivities.length > MAX_WINDOW_SIZE) {
          const excess = newActivities.length - MAX_WINDOW_SIZE
          if (direction === 'bottom') {
            console.log(`[ActivityView] Removing ${excess} activities from top`)
            newActivities = newActivities.slice(excess)
            setTopOffset((prev) => prev + excess)
          } else {
            console.log(`[ActivityView] Removing ${excess} activities from bottom`)
            newActivities = newActivities.slice(0, MAX_WINDOW_SIZE)
            setBottomOffset((prev) => prev - excess)
          }
        }

        return newActivities
      })
    } catch (err) {
      console.error(`[ActivityView] Failed to load more from ${direction}`, err)
      toast.error((err as Error).message)
    } finally {
      isLoadingRef.current = false
    }
  }

  // 刷新数据
  const handleRefresh = () => {
    void loadInitialActivities()
  }

  // 初始化加载
  useEffect(() => {
    void loadInitialActivities()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 使用无限滚动hook
  const { containerRef, sentinelTopRef, sentinelBottomRef } = useInfiniteScroll({
    onLoadMore: handleLoadMore,
    threshold: 300
  })

  const groupedActivities: GroupedActivities[] = useMemo(() => {
    if (activities.length === 0) return []

    const map = new Map<string, (ActivitySummary & { startTimestamp: number })[]>()

    for (const activity of activities) {
      const dateKey = format(new Date(activity.startTimestamp), 'yyyy-MM-dd')
      if (!map.has(dateKey)) {
        map.set(dateKey, [])
      }
      map.get(dateKey)!.push(activity)
    }

    return Array.from(map.entries())
      .sort(([dateA], [dateB]) => (dateA > dateB ? -1 : 1))
      .map(([date, items]) => ({
        date,
        activities: items.sort((a, b) => b.startTimestamp - a.startTimestamp)
      }))
  }, [activities])

  // 在渲染后尝试滚动到 focus 的活动卡片
  useEffect(() => {
    if (!focusedId) return
    const el = itemRefs.current.get(focusedId)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [focusedId, groupedActivities])

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <header className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">{t('activity.pageTitle')}</h1>
          <p className="text-muted-foreground text-sm">{t('activity.description')}</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          {t('common.refresh')}
        </Button>
      </header>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {!loading && activities.length === 0 ? (
        <div className="border-muted/60 rounded-2xl border border-dashed p-10 text-center">
          <p className="text-muted-foreground text-sm">{t('activity.noDataDescription')}</p>
        </div>
      ) : (
        <div ref={containerRef} className="flex-1 overflow-y-auto">
          <div className="flex flex-col gap-6">
            {/* 顶部哨兵 */}
            <div ref={sentinelTopRef} className="h-1 w-full" aria-hidden="true" />

            {groupedActivities.map((group) => (
              <section key={group.date} className="space-y-3">
                <header>
                  <p className="text-muted-foreground text-sm font-medium">
                    {format(new Date(group.date), 'PPP', { locale })}
                  </p>
                  <h2 className="text-lg font-semibold">
                    {group.date}
                    <span className="text-muted-foreground ml-2 text-sm">
                      {group.activities.length}
                      {t('activity.activitiesCount')}
                    </span>
                  </h2>
                </header>

                <div className="flex flex-col gap-4">
                  {group.activities.map((activity) => (
                    <div
                      key={activity.id}
                      id={`activity-${activity.id}`}
                      ref={(el) => {
                        if (el) itemRefs.current.set(activity.id, el)
                        else itemRefs.current.delete(activity.id)
                      }}>
                      <ActivityCard activity={activity} locale={locale} autoExpand={focusedId === activity.id} />
                    </div>
                  ))}
                </div>
              </section>
            ))}

            {/* 底部哨兵 */}
            <div ref={sentinelBottomRef} className="h-1 w-full" aria-hidden="true" />
          </div>
        </div>
      )}
    </div>
  )
}

interface ActivityCardProps {
  activity: ActivitySummary & { startTimestamp: number }
  locale: Locale
  autoExpand?: boolean
}

function ActivityCard({ activity, locale, autoExpand }: ActivityCardProps) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const [loadingEvents, setLoadingEvents] = useState(false)
  const [events, setEvents] = useState<ActivityEventDetail[]>([])
  const hasEvents = activity.sourceEventIds.length > 0

  const handleToggle = async () => {
    const willExpand = !expanded
    setExpanded(willExpand)

    if (willExpand && hasEvents && events.length === 0) {
      setLoadingEvents(true)
      try {
        const details = await fetchEventsByIds(activity.sourceEventIds)
        setEvents(details)
      } catch (err) {
        console.error('[ActivityCard] Failed to load events', err)
      } finally {
        setLoadingEvents(false)
      }
    }
  }

  const activityTime = format(new Date(activity.startTimestamp), 'HH:mm:ss')
  const relativeTime = formatDistanceToNow(new Date(activity.startTimestamp), { addSuffix: true, locale })

  // 当被指示自动展开时，加载事件详情并展开
  useEffect(() => {
    const run = async () => {
      if (!autoExpand || expanded || !hasEvents) return
      setExpanded(true)
      if (events.length === 0) {
        setLoadingEvents(true)
        try {
          const details = await fetchEventsByIds(activity.sourceEventIds)
          setEvents(details)
        } catch (err) {
          console.error('[ActivityCard] Failed to load events (autoExpand)', err)
        } finally {
          setLoadingEvents(false)
        }
      }
    }
    void run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoExpand])

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{activity.title || t('activity.untitled')}</CardTitle>
        <CardDescription className="flex flex-wrap items-center gap-2 text-xs">
          <span>{activityTime}</span>
          <span>·</span>
          <span>{relativeTime}</span>
          {hasEvents && (
            <Badge variant="secondary" className="rounded-full">
              {activity.sourceEventIds.length} {t('activity.eventCountLabel')}
            </Badge>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {activity.description && (
          <p className="text-muted-foreground text-sm leading-6 whitespace-pre-wrap">{activity.description}</p>
        )}

        {hasEvents && (
          <div className="bg-muted/40 rounded-md p-3">
            <button
              type="button"
              className="flex w-full items-center justify-between text-left text-sm font-medium"
              onClick={handleToggle}>
              <span>{t('activity.eventDetails')}</span>
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {expanded && (
              <div className="mt-3 space-y-3">
                {loadingEvents ? (
                  <div className="text-muted-foreground flex items-center gap-2 text-sm">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('common.loading')}
                  </div>
                ) : events.length > 0 ? (
                  events.map((event) => (
                    <div key={event.id} className="border-muted bg-background/60 rounded border p-3">
                      <p className="text-sm font-medium">{event.summary || t('activity.eventWithoutSummary')}</p>
                      <p className="text-muted-foreground mt-1 text-xs">
                        {format(new Date(event.timestamp), 'HH:mm:ss')} ·{' '}
                        {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true, locale })}
                      </p>
                      {event.keywords.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {event.keywords.map((keyword, index) => (
                            <Badge key={`${event.id}-${keyword}-${index}`} variant="outline" className="text-xs">
                              {keyword}
                            </Badge>
                          ))}
                        </div>
                      )}
                      {event.screenshots.length > 0 && (
                        <div className="mt-3 grid gap-2 sm:grid-cols-2">
                          {event.screenshots.map((image, index) => (
                            <div
                              key={`${event.id}-screenshot-${index}`}
                              className="border-muted/60 bg-background/80 overflow-hidden rounded-lg border">
                              <img
                                src={toDataUrl(image)}
                                alt={`${event.summary || activity.title || 'event'} screenshot ${index + 1}`}
                                className="h-full w-full object-cover"
                                loading="lazy"
                              />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground text-sm">{t('activity.noEventSummaries')}</p>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
