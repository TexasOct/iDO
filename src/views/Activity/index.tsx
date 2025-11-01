import { useEffect, useMemo, useState } from 'react'
import { format, formatDistanceToNow } from 'date-fns'
import type { Locale } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ActivitySummary, ActivityEventDetail, fetchActivities, fetchEventsByIds } from '@/lib/services/activityNew'

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

export default function ActivityView() {
  const { t, i18n } = useTranslation()
  const [activities, setActivities] = useState<(ActivitySummary & { startTimestamp: number })[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  const locale = useMemo(() => localeMap[i18n.language] ?? enUS, [i18n.language])

  const loadActivities = async (options: { reset?: boolean } = {}) => {
    const { reset = false } = options
    setLoading(true)
    setError(null)

    try {
      const nextOffset = reset ? 0 : offset
      const result = await fetchActivities(ACTIVITY_PAGE_SIZE, nextOffset)

      const normalized = result.map((activity) => ({
        ...activity,
        startTimestamp: Date.parse(activity.startTime || activity.createdAt || '') || Date.now()
      }))

      if (reset) {
        setActivities(normalized)
        setOffset(normalized.length)
      } else {
        setActivities((prev) => [...prev, ...normalized])
        setOffset(nextOffset + normalized.length)
      }

      setHasMore(normalized.length === ACTIVITY_PAGE_SIZE)
    } catch (err) {
      console.error('[ActivityView] Failed to fetch activities', err)
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadActivities({ reset: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t('activity.pageTitle')}</h1>
        <p className="text-muted-foreground text-sm">{t('activity.description')}</p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" size="sm" onClick={() => loadActivities({ reset: true })} disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          {t('common.refresh')}
        </Button>
      </div>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {!loading && activities.length === 0 ? (
        <div className="border-muted/60 rounded-2xl border border-dashed p-10 text-center">
          <p className="text-muted-foreground text-sm">{t('activity.noDataDescription')}</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
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

              <div className="grid gap-4 lg:grid-cols-2">
                {group.activities.map((activity) => (
                  <ActivityCard key={activity.id} activity={activity} locale={locale} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <div className="flex items-center justify-center gap-3 pb-6">
        {hasMore && (
          <Button onClick={() => loadActivities()} disabled={loading} variant="secondary">
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {t('activity.loadMore')}
          </Button>
        )}
        {loading && activities.length > 0 && <Loader2 className="text-muted-foreground h-4 w-4 animate-spin" />}
      </div>
    </div>
  )
}

interface ActivityCardProps {
  activity: ActivitySummary & { startTimestamp: number }
  locale: Locale
}

function ActivityCard({ activity, locale }: ActivityCardProps) {
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
                          {event.keywords.map((keyword) => (
                            <Badge key={keyword} variant="outline" className="text-xs">
                              {keyword}
                            </Badge>
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
