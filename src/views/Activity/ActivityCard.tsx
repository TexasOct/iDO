import { useEffect, useState } from 'react'
import type { Locale } from 'date-fns'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Loader2, ChevronDown, ChevronUp, Trash2, MessageSquare } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import {
  ActivitySummary,
  ActivityEventDetail,
  fetchEventsByIds,
  removeActivity,
  removeEvent
} from '@/lib/services/activity/item'
import { PhotoGrid } from '@/components/activity/PhotoGrid'
import { toast } from 'sonner'
import { TimeDisplay } from '@/components/shared/TimeDisplay'
import { useNavigate } from 'react-router'
import { emitActivityToChat } from '@/lib/events/eventBus'

interface ActivityCardProps {
  activity: ActivitySummary & { startTimestamp: number }
  locale: Locale
  autoExpand?: boolean
  onActivityDeleted?: (activityId: string) => void
  onEventDeleted?: (eventId: string) => void
}

export function ActivityCard({ activity, locale, autoExpand, onActivityDeleted, onEventDeleted }: ActivityCardProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)
  const [loadingEvents, setLoadingEvents] = useState(false)
  const [events, setEvents] = useState<ActivityEventDetail[]>([])
  const [deletingActivity, setDeletingActivity] = useState(false)
  const [deletingEvents, setDeletingEvents] = useState<Set<string>>(new Set())
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

  const handleDeleteActivity = async () => {
    console.log('[ActivityCard] Delete activity clicked:', activity.id)

    // 临时移除确认对话框，因为 Tauri 中 window.confirm 不工作
    // TODO: 使用更好的确认对话框组件
    setDeletingActivity(true)
    console.log('[ActivityCard] Calling removeActivity...')
    try {
      await removeActivity(activity.id)
      console.log('[ActivityCard] Activity deleted successfully')
      toast.success(t('activity.deleteActivitySuccess'))
      onActivityDeleted?.(activity.id)
    } catch (error) {
      console.error('[ActivityCard] Failed to delete activity:', error)
      toast.error(t('activity.deleteActivityError') + ': ' + (error instanceof Error ? error.message : String(error)))
    } finally {
      setDeletingActivity(false)
    }
  }

  const handleDeleteEvent = async (eventId: string) => {
    console.log('[ActivityCard] Delete event clicked:', eventId)

    // 临时移除确认对话框，因为 Tauri 中 window.confirm 不工作
    // TODO: 使用更好的确认对话框组件
    setDeletingEvents((prev) => new Set(prev).add(eventId))
    console.log('[ActivityCard] Calling removeEvent...')
    try {
      await removeEvent(eventId)
      console.log('[ActivityCard] Event deleted successfully')
      toast.success(t('activity.deleteEventSuccess'))
      setEvents((prev) => prev.filter((e) => e.id !== eventId))
      onEventDeleted?.(eventId)
    } catch (error) {
      console.error('[ActivityCard] Failed to delete event:', error)
      toast.error(t('activity.deleteEventError') + ': ' + (error instanceof Error ? error.message : String(error)))
    } finally {
      setDeletingEvents((prev) => {
        const next = new Set(prev)
        next.delete(eventId)
        return next
      })
    }
  }

  // 发送到对话
  const handleSendToChat = () => {
    toast.success('正在跳转到对话...')

    // 先跳转到 Chat
    navigate('/chat')

    // 延迟 200ms 发布事件，确保 Chat 组件已挂载并注册了事件监听器
    setTimeout(() => {
      // 暂不传递截图，避免 HTTP 431 错误（后续可按需发送）

      emitActivityToChat({
        activityId: activity.id,
        title: activity.title || t('activity.untitled'),
        description: activity.description,
        screenshots: [], // ❌ 暂不传递图片，避免 HTTP 431 错误
        keywords: activity.keywords || [],
        timestamp: activity.startTimestamp
      })
      console.log('[ActivityCard] 延迟200ms发布事件（暂不传图片）')
    }, 200)
  }

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
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <CardTitle className="text-lg">{activity.title || t('activity.untitled')}</CardTitle>
            <CardDescription className="flex flex-wrap items-center gap-2">
              <TimeDisplay timestamp={activity.startTimestamp} locale={locale} />
              {hasEvents && (
                <Badge variant="secondary" className="rounded-full text-xs">
                  {activity.sourceEventIds.length} {t('activity.eventCountLabel')}
                </Badge>
              )}
            </CardDescription>
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSendToChat}
              className="h-8 w-8 p-0"
              title="发送到对话（文字自动预填充，图片需手动添加）">
              <MessageSquare className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDeleteActivity}
              disabled={deletingActivity}
              className="text-destructive hover:text-destructive h-8 w-8 p-0">
              {deletingActivity ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            </Button>
          </div>
        </div>
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
                  <>
                    {events.map((event) => (
                      <div key={event.id} className="border-muted bg-background/60 rounded-2xl border p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <p className="text-sm font-medium">{event.summary || t('activity.eventWithoutSummary')}</p>
                            <div className="mt-1">
                              <TimeDisplay timestamp={event.timestamp} locale={locale} />
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteEvent(event.id)}
                            disabled={deletingEvents.has(event.id)}
                            className="text-destructive hover:text-destructive h-7 w-7 shrink-0 p-0">
                            {deletingEvents.has(event.id) ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Trash2 className="h-3 w-3" />
                            )}
                          </Button>
                        </div>
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
                          <div className="mt-3">
                            <PhotoGrid
                              images={event.screenshots}
                              title={event.summary || activity.title || t('activity.eventWithoutSummary')}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </>
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
