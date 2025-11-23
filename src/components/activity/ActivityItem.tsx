import { Activity, EventSummary, Event } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  MessageSquare,
  Sparkles,
  Trash2,
  FileText,
  Timer
} from 'lucide-react'
import { cn, formatDuration } from '@/lib/utils'
import { format } from 'date-fns'
import { PhotoGrid } from './PhotoGrid'
import { useTranslation } from 'react-i18next'
import { useEffect, useCallback, useMemo, useState } from 'react'
import type { MouseEvent } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { deleteActivity } from '@/lib/services/activity'
import { useScrollAnimation } from '@/hooks/useScrollAnimation'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'

interface ActivityItemProps {
  activity: Activity & { isNew?: boolean }
}

// Internal component: EventItem
function EventItem({ event }: { event: Event }) {
  const { t } = useTranslation()

  const screenshots = useMemo(() => {
    const images: string[] = []
    event.records.forEach((record) => {
      const metadata = record.metadata as { action?: string; screenshotPath?: string } | undefined
      if (metadata?.action === 'capture' && metadata.screenshotPath) {
        images.push(metadata.screenshotPath)
      }
    })
    return images
  }, [event.records])

  const title = event.summary || t('activity.eventWithoutSummary')

  if (screenshots.length === 0) {
    return (
      <div className="border-border text-muted-foreground rounded-lg border border-dashed py-6 text-center text-xs">
        {t('activity.noScreenshots')}
      </div>
    )
  }

  return (
    <div className="border-border bg-muted/30 rounded-lg border p-3 shadow-sm">
      <PhotoGrid images={screenshots} title={title} />
    </div>
  )
}

// Internal component: EventSummaryItem
function EventSummaryItem({ summary }: { summary: EventSummary }) {
  const { t } = useTranslation()
  const expandedItems = useActivityStore((state) => state.expandedItems)
  const toggleExpanded = useActivityStore((state) => state.toggleExpanded)
  const isExpanded = expandedItems.has(summary.id)

  const time = format(new Date(summary.timestamp), 'HH:mm:ss')

  const sortedEvents = useMemo(() => {
    return [...summary.events].sort((a, b) => b.startTime - a.startTime)
  }, [summary.events])

  const displayTitle =
    summary.title && summary.title.trim().length > 0 ? summary.title : t('activity.eventWithoutSummary')

  return (
    <div>
      <button onClick={() => toggleExpanded(summary.id)} className="group flex w-full items-start gap-2 py-2 text-left">
        <div className="mt-0.5">
          {isExpanded ? (
            <ChevronDown className="text-muted-foreground h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="text-muted-foreground h-3.5 w-3.5" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <FileText className="text-muted-foreground h-3.5 w-3.5" />
            <span className="group-hover:text-primary text-sm font-medium transition-colors">{displayTitle}</span>
          </div>
          <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
            <span>{time}</span>
            <span>·</span>
            <span>
              {summary.events.length}
              {t('activity.eventsCount')}
            </span>
          </div>
        </div>
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-2">
          {sortedEvents.map((event) => (
            <EventItem key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}

interface ActivityItemProps {
  activity: Activity & { isNew?: boolean }
}

export function ActivityItem({ activity }: ActivityItemProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  // Subscribe to each selector separately to avoid returning new objects
  const expandedItems = useActivityStore((state) => state.expandedItems)
  const toggleExpanded = useActivityStore((state) => state.toggleExpanded)
  const loadActivityDetails = useActivityStore((state) => state.loadActivityDetails)
  const loadingActivityDetails = useActivityStore((state) => state.loadingActivityDetails)
  const removeActivity = useActivityStore((state) => state.removeActivity)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)
  const isExpanded = expandedItems.has(activity.id)
  const isLoading = loadingActivityDetails.has(activity.id)
  const isNew = activity.isNew ?? false
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  // Scroll animation
  const { ref: elementRef, isVisible } = useScrollAnimation<HTMLDivElement>({
    threshold: 0.2,
    triggerOnce: true,
    delay: 0
  })

  // Calculate duration
  const duration = useMemo(() => {
    return activity.endTime - activity.startTime
  }, [activity.startTime, activity.endTime])

  const durationFormatted = useMemo(() => {
    return formatDuration(duration, 'short')
  }, [duration])

  // Determine if this is a milestone (long activity > 30 minutes)
  const isMilestone = useMemo(() => {
    const durationMinutes = duration / (1000 * 60)
    return durationMinutes > 30
  }, [duration])

  // Sort eventSummaries by timestamp descending (newest first)
  const sortedEventSummaries = useMemo(() => {
    if (!activity.eventSummaries) {
      console.debug('[ActivityItem] eventSummaries is null/undefined for activity:', activity.id)
      return []
    }
    console.debug(
      '[ActivityItem] eventSummaries for activity',
      activity.id,
      ':',
      activity.eventSummaries.length,
      'items'
    )
    return [...activity.eventSummaries].sort((a, b) => b.timestamp - a.timestamp)
  }, [activity.eventSummaries, activity.id])

  // Safely format time with fallback for invalid timestamps
  let time = '-- : -- : --'
  if (typeof activity.timestamp === 'number' && !isNaN(activity.timestamp)) {
    try {
      time = format(new Date(activity.timestamp), 'HH:mm:ss')
    } catch (error) {
      console.error(`[ActivityItem] Failed to format timestamp ${activity.timestamp}:`, error)
      time = '-- : -- : --'
    }
  } else {
    console.warn(`[ActivityItem] Invalid activity timestamp:`, activity.timestamp, activity.id)
  }

  // Drop the isNew flag after the entry animation completes
  useEffect(() => {
    if (isNew && elementRef.current) {
      // Animation duration (keep in sync with CSS)
      const timer = setTimeout(() => {
        if (elementRef.current) {
          elementRef.current.classList.remove('animate-in')
        }
      }, 600)
      return () => clearTimeout(timer)
    }
  }, [isNew])

  // Toggle expanded state and load detail data when opening
  const handleToggleExpanded = useCallback(async () => {
    const willBeExpanded = !isExpanded

    console.debug('[ActivityItem] Toggle expand state:', {
      activityId: activity.id,
      willBeExpanded,
      currentEventSummaries: activity.eventSummaries?.length ?? 0,
      isLoading
    })

    // Toggle expand/collapse state
    toggleExpanded(activity.id)

    // When expanding, load detail data if needed
    if (willBeExpanded && (!activity.eventSummaries || activity.eventSummaries.length === 0)) {
      console.debug('[ActivityItem] Activity expanded, start loading details:', activity.id)
      try {
        await loadActivityDetails(activity.id)
        console.debug('[ActivityItem] Activity details loaded:', activity.id)
      } catch (error) {
        console.error('[ActivityItem] Failed to load activity details:', error)
      }
    } else if (willBeExpanded) {
      console.debug('[ActivityItem] Activity already has events, skipping load:', activity.eventSummaries?.length)
    }
  }, [isExpanded, activity.id, activity.eventSummaries, toggleExpanded, loadActivityDetails, isLoading])

  // Analyze activity: navigate to Chat and associate the activity
  const handleAnalyzeActivity = useCallback(
    (e: MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation() // Prevent toggling expand/collapse
      console.debug('[ActivityItem] Analyze activity:', activity.id)
      // Navigate to the Chat page and pass the activity ID via URL params
      navigate(`/chat?activityId=${activity.id}`)
    },
    [activity.id, navigate]
  )

  const handleDeleteButtonClick = useCallback((e: MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation()
    setDeleteDialogOpen(true)
  }, [])

  const handleCancelDelete = useCallback(() => {
    if (isDeleting) {
      return
    }
    setDeleteDialogOpen(false)
  }, [isDeleting])

  const handleConfirmDelete = useCallback(async () => {
    if (isDeleting) {
      return
    }

    setIsDeleting(true)
    let deletionSucceeded = false
    try {
      deletionSucceeded = await deleteActivity(activity.id)
      if (deletionSucceeded) {
        removeActivity(activity.id)
        void fetchActivityCountByDate()
        toast.success(t('activity.deleteSuccess') || 'Activity deleted')
      } else {
        toast.error(t('activity.deleteError') || 'Failed to delete activity')
      }
    } catch (error) {
      console.error('[ActivityItem] Failed to delete activity:', error)
      toast.error(t('activity.deleteError') || 'Failed to delete activity')
    } finally {
      setIsDeleting(false)
      if (deletionSucceeded) {
        setDeleteDialogOpen(false)
      }
    }
  }, [activity.id, fetchActivityCountByDate, isDeleting, removeActivity, t])

  return (
    <div
      ref={elementRef}
      className={cn(
        'relative transition-all duration-700',
        isNew && 'animate-in fade-in slide-in-from-top-2 duration-500',
        isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
      )}>
      {/* Timeline axis and nodes removed for cleaner design */}

      <div className="border-border/80 bg-card group hover:border-primary/50 hover:shadow-primary/10 relative overflow-hidden rounded-lg border p-5 shadow-md transition-all duration-300 hover:shadow-xl">
        {/* Subtle background gradient for depth */}
        <div className="from-primary/5 pointer-events-none absolute inset-0 bg-linear-to-br to-transparent" />

        {/* Progress indicator bar based on duration */}
        <div
          className="bg-primary/10 absolute right-0 bottom-0 left-0 h-1 overflow-hidden"
          title={`Duration: ${durationFormatted}`}>
          <div
            className="bg-primary h-full transition-all duration-1000"
            style={{
              width: `${Math.min((duration / (1000 * 60 * 60)) * 100, 100)}%` // Scale by hour
            }}
          />
        </div>

        <div className="relative z-10 space-y-4">
          <div className="flex items-start gap-3">
            <button
              onClick={handleToggleExpanded}
              className="border-border hover:border-primary mt-0.5 rounded-full border p-1 transition">
              {isLoading ? (
                <Loader2 className="text-muted-foreground h-3.5 w-3.5 animate-spin" />
              ) : isExpanded ? (
                <ChevronDown className="text-muted-foreground h-3.5 w-3.5" />
              ) : (
                <ChevronRight className="text-muted-foreground h-3.5 w-3.5" />
              )}
            </button>

            <div onClick={handleToggleExpanded} className="min-w-0 flex-1 cursor-pointer space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <div className="text-muted-foreground flex items-center gap-2 text-[11px] tracking-[0.3em] uppercase">
                  <Clock className="h-3 w-3" />
                  <span>{time}</span>
                </div>
                <div className="text-primary flex items-center gap-1.5 text-xs font-medium">
                  <Timer className="h-3.5 w-3.5" />
                  <span>{durationFormatted}</span>
                </div>
                {isMilestone && (
                  <Badge variant="default" className="bg-primary rounded-full px-3 text-[10px]">
                    <Sparkles className="mr-1 h-2.5 w-2.5" />
                    {t('activity.milestone', 'Milestone')}
                  </Badge>
                )}
              </div>

              <div className="space-y-1">
                <h3 className="text-foreground text-lg font-semibold">{activity.title || t('activity.untitled')}</h3>
                {!isExpanded && activity.description && (
                  <p className="text-muted-foreground line-clamp-2 text-sm leading-relaxed">{activity.description}</p>
                )}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleAnalyzeActivity}
                className="h-8 w-8"
                title={t('activity.analyzeInChat')}>
                <MessageSquare className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDeleteButtonClick}
                className="text-destructive hover:text-destructive h-8 w-8"
                title={t('activity.deleteActivity')}
                disabled={isDeleting}>
                {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          {isExpanded && activity.description && (
            <div className="border-primary/20 bg-primary/5 text-foreground rounded-lg border p-4 text-sm leading-relaxed">
              <div className="text-primary mb-2 flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                <span className="text-xs font-semibold tracking-widest uppercase">{t('activity.summary')}</span>
              </div>
              <p className="whitespace-pre-wrap">{activity.description}</p>
            </div>
          )}

          {isExpanded && (
            <div className="space-y-3">
              <div className="text-muted-foreground flex items-center gap-2 text-xs font-semibold tracking-widest uppercase">
                <FileText className="h-4 w-4" />
                {t('activity.relatedEvents')} ({sortedEventSummaries.length})
              </div>
              {isLoading ? (
                <div className="border-border text-muted-foreground flex items-center justify-center gap-2 rounded-lg border border-dashed py-6 text-xs">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {t('common.loading')}
                </div>
              ) : sortedEventSummaries.length > 0 ? (
                <div className="relative">
                  <div className="from-primary/30 via-border absolute top-0 bottom-0 left-2 w-px to-transparent" />
                  <div className="space-y-4">
                    {sortedEventSummaries.map((summary) => (
                      <div key={summary.id} className="relative">
                        <EventSummaryItem summary={summary} />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="border-border text-muted-foreground rounded-lg border border-dashed py-6 text-center text-xs">
                  {t('activity.noEventSummaries')}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <Dialog
        open={deleteDialogOpen}
        onOpenChange={(open) => {
          if (!isDeleting) {
            setDeleteDialogOpen(open)
          }
        }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('activity.deleteActivity')}</DialogTitle>
            <DialogDescription>{t('activity.deleteConfirmPrompt')}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleCancelDelete} disabled={isDeleting}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete} disabled={isDeleting}>
              {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
