import { Activity } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Clock, Loader2, MessageSquare, Sparkles, Trash2, Timer, Layers, ChevronDown, ChevronUp } from 'lucide-react'
import { EventCard } from './EventCard'
import { ActionCard } from './ActionCard'
import { cn, formatDuration } from '@/lib/utils'
import { format } from 'date-fns'
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
import { Checkbox } from '@/components/ui/checkbox'

interface ActivityItemProps {
  activity: Activity & { isNew?: boolean }
  selectionMode?: boolean
  isSelected?: boolean
  onToggleSelection?: (activityId: string) => void
}

export function ActivityItem({
  activity,
  selectionMode = false,
  isSelected = false,
  onToggleSelection
}: ActivityItemProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  // Three-layer architecture drill-down
  const expandedActivityId = useActivityStore((state) => state.expandedActivityId)
  const expandedEvents = useActivityStore((state) => state.expandedEvents)
  const loadingEvents = useActivityStore((state) => state.loadingEvents)
  const expandedEventId = useActivityStore((state) => state.expandedEventId)
  const expandedActions = useActivityStore((state) => state.expandedActions)
  const loadingActions = useActivityStore((state) => state.loadingActions)
  const fetchActionsByEvent = useActivityStore((state) => state.fetchActionsByEvent)
  const toggleActivityDrillDown = useActivityStore((state) => state.toggleActivityDrillDown)
  const toggleEventDrillDown = useActivityStore((state) => state.toggleEventDrillDown)
  const removeActivity = useActivityStore((state) => state.removeActivity)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)

  const isNew = activity.isNew ?? false
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(false)

  // Three-layer drill-down state
  const isDrilledDown = expandedActivityId === activity.id

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

  // Safely format time range with fallback for invalid timestamps
  let timeRange = '-- : -- : -- ~ -- : -- : --'
  if (
    typeof activity.startTime === 'number' &&
    !isNaN(activity.startTime) &&
    typeof activity.endTime === 'number' &&
    !isNaN(activity.endTime)
  ) {
    try {
      const startTimeStr = format(new Date(activity.startTime), 'HH:mm:ss')
      const endTimeStr = format(new Date(activity.endTime), 'HH:mm:ss')
      timeRange = `${startTimeStr} ~ ${endTimeStr}`
    } catch (error) {
      console.error(`[ActivityItem] Failed to format time range ${activity.startTime} - ${activity.endTime}:`, error)
      timeRange = '-- : -- : -- ~ -- : -- : --'
    }
  } else {
    console.warn(`[ActivityItem] Invalid activity time range:`, activity.startTime, activity.endTime, activity.id)
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

  // Ensure "View Actions" opens or refreshes the action list instead of collapsing the event
  const handleViewActions = useCallback(
    (eventId: string) => {
      if (expandedEventId !== eventId) {
        toggleEventDrillDown(eventId)
        return
      }

      void fetchActionsByEvent(eventId)
    },
    [expandedEventId, fetchActionsByEvent, toggleEventDrillDown]
  )

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

  const handleToggleSummary = useCallback((e: MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation()
    setIsSummaryExpanded((prev) => !prev)
  }, [])

  return (
    <div
      ref={elementRef}
      className={cn(
        'relative transition-all duration-700',
        isNew && 'animate-in fade-in slide-in-from-top-2 duration-500',
        isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
      )}>
      {/* Timeline axis and nodes removed for cleaner design */}

      <div className="border-border/80 bg-card group hover:border-primary/50 hover:shadow-primary/10 relative overflow-hidden rounded-lg border p-3 shadow-md transition-all duration-300 hover:shadow-xl">
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

        <div className="relative z-10 space-y-2">
          {/* Action buttons - absolutely positioned */}
          <div className="absolute top-0 right-0 z-20 flex items-center gap-1">
            {activity.description && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleToggleSummary}
                className="h-8 w-8"
                title={isSummaryExpanded ? t('activity.showLess', 'Show less') : t('activity.showMore', 'Show more')}>
                {isSummaryExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            )}
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

          <div className="flex items-start gap-2 p-4">
            {/* Selection checkbox (only shown in selection mode) */}
            {selectionMode && (
              <div className="mt-0.5">
                <Checkbox checked={isSelected} onCheckedChange={() => onToggleSelection?.(activity.id)} />
              </div>
            )}

            <div className="min-w-0 flex-1 space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <div className="text-muted-foreground flex items-center gap-1.5 text-[11px] tracking-[0.3em] uppercase">
                  <Clock className="h-3 w-3" />
                  <span>{timeRange}</span>
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

              <div className="space-y-1.5">
                <h3 className="text-foreground text-lg leading-relaxed font-semibold">
                  {activity.title || t('activity.untitled')}
                </h3>
                {activity.description && (
                  <div className="bg-muted/50 hover:bg-muted/70 rounded-lg border border-transparent p-2 transition-colors">
                    <div className="flex items-start gap-2">
                      <Sparkles className="text-primary mt-0.5 h-4 w-4 shrink-0" />
                      <p
                        className={cn(
                          'text-foreground/90 min-w-0 flex-1 text-sm leading-relaxed',
                          !isSummaryExpanded && 'line-clamp-2'
                        )}>
                        {activity.description}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Three-layer architecture drill-down */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-muted-foreground flex items-center gap-2 text-xs font-semibold tracking-widest uppercase">
                <Layers className="h-4 w-4" />
                Events
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => toggleActivityDrillDown(activity.id)}
                className="h-7 text-xs">
                {isDrilledDown ? 'Hide Events' : 'View Events'}
                {loadingEvents && <Loader2 className="ml-2 h-3 w-3 animate-spin" />}
              </Button>
            </div>

            {isDrilledDown && (
              <div className="space-y-2">
                {loadingEvents ? (
                  <div className="border-border text-muted-foreground flex items-center justify-center gap-2 rounded-lg border border-dashed py-6 text-xs">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Loading Events...
                  </div>
                ) : expandedEvents.length > 0 ? (
                  <div className="space-y-2">
                    {expandedEvents.map((event) => (
                      <div key={event.id}>
                        <EventCard
                          event={event}
                          isExpanded={expandedEventId === event.id}
                          onToggleExpand={() => toggleEventDrillDown(event.id)}
                          onViewActions={() => handleViewActions(event.id)}
                          actionsCount={event.sourceActionIds?.length ?? 0}
                        />

                        {/* Actions drill-down */}
                        {expandedEventId === event.id && (
                          <div className="mt-2 ml-7 space-y-2">
                            {loadingActions ? (
                              <div className="border-border text-muted-foreground flex items-center justify-center gap-2 rounded-md border border-dashed py-4 text-xs">
                                <Loader2 className="h-3 w-3 animate-spin" />
                                Loading Actions...
                              </div>
                            ) : expandedActions.length > 0 ? (
                              expandedActions.map((action) => <ActionCard key={action.id} action={action} />)
                            ) : (
                              <div className="border-border text-muted-foreground rounded-md border border-dashed py-4 text-center text-xs">
                                No actions found
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="border-border text-muted-foreground rounded-lg border border-dashed py-6 text-center text-xs">
                    No events found
                  </div>
                )}
              </div>
            )}
          </div>
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
