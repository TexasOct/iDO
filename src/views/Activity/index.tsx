import { useEffect, useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { addDays, subDays, startOfDay, endOfDay, parseISO, getHours, getMinutes, format } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'
import type { Locale } from 'date-fns'
import { Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { TimelineGrid } from '@/components/activity/TimelineGrid'
import { ActivitySummary, ActivityEventDetail, fetchActivities, fetchEventsByIds } from '@/lib/services/activity/item'
import { PhotoGrid } from '@/components/activity/PhotoGrid'
import { toast } from 'sonner'
import { PageLayout } from '@/components/layout/PageLayout'

const localeMap: Record<string, Locale> = {
  zh: zhCN,
  'zh-CN': zhCN,
  en: enUS,
  'en-US': enUS
}

/**
 * Activity view with calendar-style timeline layout
 * Features:
 * - Date navigation (previous/next day)
 * - Record toggle switch
 * - Hourly timeline slots with activity blocks
 * - Right sidebar for selected activity details
 */
export default function ActivityView() {
  const { t, i18n } = useTranslation()
  const locale = useMemo(() => localeMap[i18n.language] ?? enUS, [i18n.language])
  const [currentDate, setCurrentDate] = useState(new Date())
  const [activities, setActivities] = useState<ActivitySummary[]>([])
  const [selectedActivity, setSelectedActivity] = useState<ActivitySummary | null>(null)
  const [selectedEvents, setSelectedEvents] = useState<ActivityEventDetail[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingEvents, setLoadingEvents] = useState(false)

  // Load activities for current date
  useEffect(() => {
    const loadActivities = async () => {
      setLoading(true)
      try {
        // TODO: Implement date filtering in backend API
        const allActivities = await fetchActivities(100, 0)

        // Filter activities for current date
        const dayStart = startOfDay(currentDate).getTime()
        const dayEnd = endOfDay(currentDate).getTime()

        const filtered = allActivities.filter((activity) => {
          const activityTime = parseISO(activity.startTime).getTime()
          return activityTime >= dayStart && activityTime <= dayEnd
        })

        setActivities(filtered)
      } catch (error) {
        console.error('[ActivityView] Failed to load activities:', error)
        toast.error(t('activity.loadingData'))
      } finally {
        setLoading(false)
      }
    }

    void loadActivities()
  }, [currentDate, t])

  const handlePreviousDay = () => {
    setCurrentDate((prev) => subDays(prev, 1))
    setSelectedActivity(null)
  }

  const handleNextDay = () => {
    setCurrentDate((prev) => addDays(prev, 1))
    setSelectedActivity(null)
  }

  const handleActivityClick = async (activity: ActivitySummary) => {
    setSelectedActivity(activity)
    setSelectedEvents([])

    // Load events for this activity
    if (activity.sourceEventIds.length > 0) {
      setLoadingEvents(true)
      try {
        const events = await fetchEventsByIds(activity.sourceEventIds)
        setSelectedEvents(events)
      } catch (error) {
        console.error('[ActivityView] Failed to load events:', error)
        toast.error(t('activity.loadingData'))
      } finally {
        setLoadingEvents(false)
      }
    }
  }

  // Calculate activity position in timeline (top offset and height)
  const getActivityPosition = (activity: ActivitySummary) => {
    const start = parseISO(activity.startTime)

    const startHour = getHours(start)
    const startMinute = getMinutes(start)

    // Each hour slot is 64px (h-16 = 4rem = 64px)
    const hourHeight = 64
    const topOffset = (startHour + startMinute / 60) * hourHeight

    // Fixed 30 minutes (0.5 hour) display height for all activities
    const fixedDuration = 0.5
    const height = fixedDuration * hourHeight

    return { top: topOffset, height }
  }

  return (
    <PageLayout>
      {/* Header */}
      <div className="border-border/40 flex items-center justify-between border-b px-6 py-4">
        <h1 className="text-2xl font-semibold">{format(currentDate, 'PPP', { locale })}</h1>
      </div>

      {/* Main Content: Timeline + Sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Timeline Area */}
        <div className="relative flex-1 overflow-hidden px-4 pt-4">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
            </div>
          ) : (
            <TimelineGrid startHour={0} endHour={24}>
              {/* Activity blocks */}
              {activities.map((activity) => {
                const { top, height } = getActivityPosition(activity)
                const isSelected = selectedActivity?.id === activity.id

                return (
                  <button
                    key={activity.id}
                    type="button"
                    onClick={() => handleActivityClick(activity)}
                    className={`absolute right-8 left-24 overflow-hidden rounded-md px-2.5 py-1.5 text-left text-xs transition-all hover:shadow-md ${isSelected ? 'bg-primary text-primary-foreground ring-primary shadow-lg ring-2' : 'bg-primary/10 text-foreground hover:bg-primary/20 shadow-sm'}`}
                    style={{
                      top: `${top}px`,
                      height: `${height}px`
                    }}>
                    <div className="line-clamp-1 font-semibold">{activity.title || t('activity.untitled')}</div>
                    {height > 40 && activity.description && (
                      <div className="text-muted-foreground mt-0.5 line-clamp-2 text-xs opacity-80">
                        {activity.description}
                      </div>
                    )}
                  </button>
                )
              })}
            </TimelineGrid>
          )}

          {/* Floating Navigation Buttons */}
          <div className="pointer-events-none fixed right-100 bottom-6 z-50 flex gap-3">
            <button
              onClick={handlePreviousDay}
              className="bg-primary text-primary-foreground hover:bg-primary/90 pointer-events-auto flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-all hover:scale-110"
              aria-label="Previous day">
              <ChevronLeft className="h-6 w-6" />
            </button>
            <button
              onClick={handleNextDay}
              className="bg-primary text-primary-foreground hover:bg-primary/90 pointer-events-auto flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-all hover:scale-110"
              aria-label="Next day">
              <ChevronRight className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="border-border/40 bg-background w-96 shrink-0 overflow-y-auto border-l p-6">
          {selectedActivity ? (
            <div className="space-y-4">
              {/* Activity Title */}
              <h2 className="text-xl font-bold">{selectedActivity.title || t('activity.untitled')}</h2>

              {/* Time and Keywords */}
              <div className="space-y-2">
                <p className="text-muted-foreground text-sm">
                  {format(parseISO(selectedActivity.startTime), 'PPp', { locale })}
                </p>
                {selectedActivity.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {selectedActivity.keywords.map((keyword, index) => (
                      <span
                        key={`${selectedActivity.id}-${keyword}-${index}`}
                        className="bg-secondary rounded-full px-2.5 py-1 text-xs">
                        {keyword}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Description */}
              {selectedActivity.description && (
                <div className="text-sm leading-relaxed">{selectedActivity.description}</div>
              )}

              {/* Events Section */}
              {selectedActivity.sourceEventIds.length > 0 && (
                <div className="border-border/40 space-y-3 border-t pt-4">
                  <h3 className="text-sm font-semibold">
                    {t('activity.eventDetails')} ({selectedActivity.sourceEventIds.length})
                  </h3>

                  {loadingEvents ? (
                    <div className="text-muted-foreground flex items-center gap-2 text-sm">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {t('common.loading')}
                    </div>
                  ) : selectedEvents.length > 0 ? (
                    <div className="space-y-3">
                      {selectedEvents.map((event) => (
                        <div key={event.id} className="border-border space-y-2 rounded-lg border p-3">
                          {/* Event Summary */}
                          {event.summary && <p className="text-sm font-medium">{event.summary}</p>}

                          {/* Event Time */}
                          <p className="text-muted-foreground text-xs">
                            {format(new Date(event.timestamp), 'PPp', { locale })}
                          </p>

                          {/* Event Keywords */}
                          {event.keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {event.keywords.map((keyword, index) => (
                                <span
                                  key={`${event.id}-${keyword}-${index}`}
                                  className="bg-muted rounded-full px-2 py-0.5 text-xs">
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Screenshots */}
                          {event.screenshots.length > 0 && (
                            <PhotoGrid
                              images={event.screenshots}
                              title={event.summary || selectedActivity.title || t('activity.untitled')}
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-sm">{t('activity.noEventSummaries')}</p>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-muted-foreground flex h-full flex-col items-center justify-center text-center">
              <h3 className="text-foreground mb-2 text-lg font-semibold">{t('activity.noCardsYet')}</h3>
              <p className="text-sm leading-relaxed">{t('activity.cardsGenerationHint')}</p>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
