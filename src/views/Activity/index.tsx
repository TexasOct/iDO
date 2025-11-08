import { useEffect, useMemo, useState, useRef } from 'react'
import { useSearchParams } from 'react-router'
import { format } from 'date-fns'
import type { Locale } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Loader2, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ActivitySummary, fetchActivities } from '@/lib/services/activityNew'
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll'
import { toast } from 'sonner'
import { ActivityCard } from './ActivityCard'

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
                      <ActivityCard
                        activity={activity}
                        locale={locale}
                        autoExpand={focusedId === activity.id}
                        onActivityDeleted={(activityId) => {
                          setActivities((prev) => prev.filter((a) => a.id !== activityId))
                        }}
                        onEventDeleted={(eventId) => {
                          console.log('[ActivityView] Event deleted:', eventId)
                        }}
                      />
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
