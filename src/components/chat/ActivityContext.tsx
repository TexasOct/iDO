/**
 * ActivityContext 组件（新架构）
 * 显示关联活动及其事件概要
 */

import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { X, Link2, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'
import type { Locale } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'
import { ActivityEventDetail, ActivitySummary, fetchActivityById, fetchEventsByIds } from '@/lib/services/activityNew'

interface ActivityContextProps {
  activityId: string
  onDismiss: () => void
}

const localeMap: Record<string, Locale> = {
  zh: zhCN,
  'zh-CN': zhCN,
  en: enUS,
  'en-US': enUS
}

export function ActivityContext({ activityId, onDismiss }: ActivityContextProps) {
  const { t, i18n } = useTranslation()
  const [activity, setActivity] = useState<ActivitySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [eventDetails, setEventDetails] = useState<ActivityEventDetail[]>([])
  const [loadingEvents, setLoadingEvents] = useState(false)
  const locale = useMemo(() => localeMap[i18n.language] ?? enUS, [i18n.language])

  useEffect(() => {
    let mounted = true

    const load = async () => {
      setLoading(true)
      try {
        const data = await fetchActivityById(activityId)
        if (mounted) {
          setActivity(data)
          setExpanded(false)
          setEventDetails([])
        }
      } catch (error) {
        console.error('[ActivityContext] Failed to fetch activity', error)
        if (mounted) {
          setActivity(null)
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      mounted = false
    }
  }, [activityId])

  useEffect(() => {
    if (!expanded || !activity || eventDetails.length > 0 || activity.sourceEventIds.length === 0) {
      return
    }

    let mounted = true

    const loadEvents = async () => {
      setLoadingEvents(true)
      try {
        const details = await fetchEventsByIds(activity.sourceEventIds)
        if (mounted) {
          setEventDetails(details)
        }
      } catch (error) {
        console.error('[ActivityContext] Failed to fetch event summaries', error)
      } finally {
        if (mounted) {
          setLoadingEvents(false)
        }
      }
    }

    void loadEvents()

    return () => {
      mounted = false
    }
  }, [expanded, activity, eventDetails.length])

  if (loading) {
    return (
      <div className="border-primary/30 bg-primary/5 flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
        <Link2 className="text-primary h-3.5 w-3.5" />
        <span className="text-muted-foreground">{t('chat.loadingContext')}</span>
      </div>
    )
  }

  if (!activity) {
    return null
  }

  const timestamp = Date.parse(activity.startTime || activity.createdAt || '')
  const formattedTime = format(isNaN(timestamp) ? new Date() : new Date(timestamp), 'HH:mm:ss')

  return (
    <div className="border-primary/30 bg-primary/5 w-full max-w-full min-w-0 overflow-hidden rounded-md border">
      <div className="flex w-full flex-wrap items-center gap-2 px-3 py-2">
        <Link2 className="text-primary h-3.5 w-3.5 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="flex w-full flex-wrap items-center gap-2">
            <span className="text-primary text-xs font-medium">{t('chat.relatedActivity')}</span>
            <span className="text-foreground truncate overflow-hidden text-sm font-medium">
              {activity.title || t('activity.untitled')}
            </span>
            <span className="text-muted-foreground flex-shrink-0 text-xs">({formattedTime})</span>
          </div>
        </div>
        {activity.sourceEventIds.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded((value) => !value)}
            className="text-muted-foreground hover:text-foreground h-6 shrink-0 px-1.5 text-xs"
            title={expanded ? t('chat.hideDetails') : t('chat.viewDetails')}>
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          className="text-muted-foreground hover:text-foreground h-6 w-6 shrink-0 p-0"
          title={t('common.cancel')}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {expanded && (
        <div className="border-primary/20 border-t px-3 py-2">
          {loadingEvents ? (
            <div className="text-muted-foreground flex items-center gap-2 text-xs">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {t('common.loading')}
            </div>
          ) : (
            <div className="max-h-60 w-full space-y-2 overflow-y-auto pr-1">
              {activity.description && (
                <div className="text-muted-foreground text-xs break-words whitespace-pre-wrap">
                  <span className="font-medium">{t('activity.details')}: </span>
                  {activity.description}
                </div>
              )}

              {eventDetails.length > 0 ? (
                <div className="text-muted-foreground space-y-1 text-xs">
                  <div className="font-medium">
                    {t('activity.eventCountLabel')}: {eventDetails.length}
                  </div>
                  {eventDetails.slice(0, 5).map((event) => (
                    <div key={event.id} className="border-muted/60 bg-background/40 rounded border p-2">
                      <div className="text-foreground font-semibold">
                        {event.summary || t('activity.eventWithoutSummary')}
                      </div>
                      <div className="mt-1 text-[11px]">
                        {format(new Date(event.timestamp), 'HH:mm:ss')} ·{' '}
                        {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true, locale })}
                      </div>
                      {event.keywords.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {event.keywords.map((keyword) => (
                            <span key={keyword} className="bg-muted rounded px-1 py-0.5 text-[11px]">
                              {keyword}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                  {eventDetails.length > 5 && (
                    <div>
                      … {t('common.and')} {eventDetails.length - 5} {t('common.more')}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-muted-foreground text-xs">{t('activity.noEventSummaries')}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
