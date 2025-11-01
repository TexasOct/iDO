import { useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { Locale } from 'date-fns'
import { formatDistanceToNow } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useInsightsStore } from '@/lib/stores/insights'
import { toast } from 'sonner'

const localeMap: Record<string, Locale> = {
  zh: zhCN,
  'zh-CN': zhCN,
  en: enUS,
  'en-US': enUS
}

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

  const recentEvents = useInsightsStore((state) => state.recentEvents)
  const loadingEvents = useInsightsStore((state) => state.loadingEvents)
  const fetchRecentEvents = useInsightsStore((state) => state.fetchRecentEvents)
  const setRecentEventsLimit = useInsightsStore((state) => state.setRecentEventsLimit)
  const recentEventsLimit = useInsightsStore((state) => state.recentEventsLimit)
  const lastError = useInsightsStore((state) => state.lastError)
  const clearError = useInsightsStore((state) => state.clearError)

  const locale = useMemo(() => localeMap[i18n.language] ?? enUS, [i18n.language])

  useEffect(() => {
    fetchRecentEvents(recentEventsLimit)
  }, [fetchRecentEvents, recentEventsLimit])

  useEffect(() => {
    if (!lastError) return
    toast.error(lastError)
    clearError()
  }, [lastError, clearError])

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t('insights.eventsPageTitle')}</h1>
        <p className="text-muted-foreground text-sm">{t('insights.eventsPageDescription')}</p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-muted-foreground text-sm font-medium" htmlFor="event-limit">
          {t('insights.eventsLimitLabel')}
        </label>
        <Input
          id="event-limit"
          type="number"
          min={1}
          max={100}
          value={recentEventsLimit}
          className="w-24"
          onChange={(event) => {
            const value = Math.max(1, Number(event.target.value) || 1)
            setRecentEventsLimit(value)
          }}
        />
        <Button
          size="sm"
          onClick={() => fetchRecentEvents(recentEventsLimit)}
          disabled={loadingEvents}
          className="flex items-center gap-2">
          {loadingEvents ? t('insights.loading') : t('common.refresh')}
        </Button>
      </div>

      {loadingEvents && recentEvents.length === 0 ? (
        <p className="text-muted-foreground text-sm">{t('insights.loading')}</p>
      ) : recentEvents.length === 0 ? (
        <div className="rounded-xl border border-dashed p-8 text-center">
          <p className="text-muted-foreground text-sm">{t('insights.noRecentEvents')}</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {recentEvents.map((event) => (
            <Card key={event.id}>
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
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
