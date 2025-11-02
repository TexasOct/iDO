import { useEffect, useMemo, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { Locale } from 'date-fns'
import { formatDistanceToNow } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, RefreshCw } from 'lucide-react'
import { fetchRecentEvents, type InsightEvent } from '@/lib/services/insights'
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll'
import { toast } from 'sonner'

const localeMap: Record<string, Locale> = {
  zh: zhCN,
  'zh-CN': zhCN,
  en: enUS,
  'en-US': enUS
}

const EVENTS_PAGE_SIZE = 20
const MAX_WINDOW_SIZE = 100 // 滑动窗口最大容量
const toDataUrl = (value: string) => (value.startsWith('data:') ? value : `data:image/jpeg;base64,${value}`)

const formatRelative = (timestamp?: string, locale?: Locale) => {
  if (!timestamp) return ''
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return ''
  try {
    return formatDistanceToNow(parsed, { addSuffix: true, locale })
  } catch (error) {
    console.error('Failed to format timestamp', error)
    return ''
  }
}

export default function RecentEventsView() {
  const { t, i18n } = useTranslation()
  const [events, setEvents] = useState<InsightEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [topOffset, setTopOffset] = useState(0) // 顶部偏移
  const [bottomOffset, setBottomOffset] = useState(0) // 底部偏移
  const [hasMoreTop, setHasMoreTop] = useState(false) // 顶部是否有更多
  const [hasMoreBottom, setHasMoreBottom] = useState(true) // 底部是否有更多
  const isLoadingRef = useRef(false)

  const locale = useMemo(() => localeMap[i18n.language] ?? enUS, [i18n.language])

  // 加载初始数据
  const loadInitialEvents = async () => {
    if (isLoadingRef.current) return
    isLoadingRef.current = true
    setLoading(true)
    setError(null)

    try {
      const result = await fetchRecentEvents(EVENTS_PAGE_SIZE, 0)
      setEvents(result)
      setTopOffset(0)
      setBottomOffset(result.length)
      setHasMoreTop(false)
      setHasMoreBottom(result.length === EVENTS_PAGE_SIZE)
    } catch (err) {
      console.error('[RecentEventsView] Failed to fetch initial events', err)
      const errorMessage = (err as Error).message
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
      isLoadingRef.current = false
    }
  }

  // 处理滚动加载（顶部或底部）
  const handleLoadMore = async (direction: 'top' | 'bottom') => {
    if (isLoadingRef.current) return

    // 检查是否还有更多数据
    if (direction === 'top' && !hasMoreTop) return
    if (direction === 'bottom' && !hasMoreBottom) return

    isLoadingRef.current = true
    console.log(`[RecentEventsView] Loading more from ${direction}`)

    try {
      const offset = direction === 'top' ? topOffset : bottomOffset
      const result = await fetchRecentEvents(EVENTS_PAGE_SIZE, offset)

      if (result.length === 0) {
        // 没有更多数据
        if (direction === 'top') {
          setHasMoreTop(false)
        } else {
          setHasMoreBottom(false)
        }
        return
      }

      setEvents((prev) => {
        let newEvents: InsightEvent[]

        if (direction === 'top') {
          // 顶部加载：添加到前面
          newEvents = [...result, ...prev]
          setTopOffset(offset + result.length)
          setHasMoreTop(result.length === EVENTS_PAGE_SIZE)
        } else {
          // 底部加载：添加到后面
          newEvents = [...prev, ...result]
          setBottomOffset(offset + result.length)
          setHasMoreBottom(result.length === EVENTS_PAGE_SIZE)
        }

        // 滑动窗口管理：保持窗口大小在 MAX_WINDOW_SIZE
        if (newEvents.length > MAX_WINDOW_SIZE) {
          const excess = newEvents.length - MAX_WINDOW_SIZE
          if (direction === 'bottom') {
            // 底部加载时，移除顶部元素
            console.log(`[RecentEventsView] Removing ${excess} events from top`)
            newEvents = newEvents.slice(excess)
            setTopOffset((prev) => prev + excess)
          } else {
            // 顶部加载时，移除底部元素
            console.log(`[RecentEventsView] Removing ${excess} events from bottom`)
            newEvents = newEvents.slice(0, MAX_WINDOW_SIZE)
            setBottomOffset((prev) => prev - excess)
          }
        }

        return newEvents
      })
    } catch (err) {
      console.error(`[RecentEventsView] Failed to load more from ${direction}`, err)
      toast.error((err as Error).message)
    } finally {
      isLoadingRef.current = false
    }
  }

  // 刷新数据
  const handleRefresh = () => {
    void loadInitialEvents()
  }

  // 初始化加载
  useEffect(() => {
    void loadInitialEvents()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 使用无限滚动hook
  const { containerRef, sentinelTopRef, sentinelBottomRef } = useInfiniteScroll({
    onLoadMore: handleLoadMore,
    threshold: 300
  })

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <header className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">{t('insights.eventsPageTitle')}</h1>
          <p className="text-muted-foreground text-sm">{t('insights.eventsPageDescription')}</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          {t('common.refresh')}
        </Button>
      </header>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {!loading && events.length === 0 ? (
        <div className="border-muted/60 rounded-2xl border border-dashed p-10 text-center">
          <p className="text-muted-foreground text-sm">{t('insights.noRecentEvents')}</p>
        </div>
      ) : (
        <div ref={containerRef} className="flex-1 overflow-y-auto">
          <div className="flex flex-col gap-4">
            {/* 顶部哨兵 */}
            <div ref={sentinelTopRef} className="h-1 w-full" aria-hidden="true" />

            {events.map((event) => (
              <Card key={event.id} className="shadow-sm">
                <CardHeader>
                  <CardTitle className="text-lg">
                    {event.title || event.description || t('insights.untitledEvent')}
                  </CardTitle>
                  <CardDescription>{formatRelative(event.timestamp, locale)}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {event.description && <p className="text-muted-foreground text-sm leading-6">{event.description}</p>}
                  {event.keywords && event.keywords.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {event.keywords.slice(0, 6).map((keyword) => (
                        <Badge key={keyword} variant="secondary">
                          {keyword}
                        </Badge>
                      ))}
                      {event.keywords.length > 6 && (
                        <span className="text-muted-foreground text-xs">+{event.keywords.length - 6}</span>
                      )}
                    </div>
                  )}
                  {event.screenshots.length > 0 && (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {event.screenshots.map((image, index) => (
                        <div
                          key={`${event.id}-screenshot-${index}`}
                          className="border-muted/60 bg-background/80 overflow-hidden rounded-lg border">
                          <img
                            src={toDataUrl(image)}
                            alt={`${event.title || event.description || 'event'} screenshot ${index + 1}`}
                            className="h-full w-full object-cover"
                            loading="lazy"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}

            {/* 底部哨兵 */}
            <div ref={sentinelBottomRef} className="h-1 w-full" aria-hidden="true" />
          </div>
        </div>
      )}
    </div>
  )
}
