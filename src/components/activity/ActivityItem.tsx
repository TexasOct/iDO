import { Activity, EventSummary, Event } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ChevronDown, ChevronRight, Clock, Loader2, MessageSquare, Sparkles, Trash2, FileText } from 'lucide-react'
import { format } from 'date-fns'
import { PhotoGrid } from './PhotoGrid'
import { useTranslation } from 'react-i18next'
import { useEffect, useRef, useCallback, useMemo, useState } from 'react'
import type { MouseEvent } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { deleteActivity } from '@/lib/services/activity'
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
      <div className="text-muted-foreground border-border/40 rounded-2xl border border-dashed py-6 text-center text-xs">
        {t('activity.noScreenshots')}
      </div>
    )
  }

  return (
    <div className="border-border/40 bg-background/80 rounded-3xl border p-3 shadow-sm">
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
    <div className="border-muted border-l-2 pl-4">
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
  // 分别订阅各个字段，避免选择器返回新对象
  const expandedItems = useActivityStore((state) => state.expandedItems)
  const toggleExpanded = useActivityStore((state) => state.toggleExpanded)
  const loadActivityDetails = useActivityStore((state) => state.loadActivityDetails)
  const loadingActivityDetails = useActivityStore((state) => state.loadingActivityDetails)
  const removeActivity = useActivityStore((state) => state.removeActivity)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)
  const isExpanded = expandedItems.has(activity.id)
  const isLoading = loadingActivityDetails.has(activity.id)
  const isNew = activity.isNew ?? false
  const elementRef = useRef<HTMLDivElement>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  // 按时间倒序排序 eventSummaries（最新的在上面）
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

  // 新活动进入时移除 isNew 标记（动画完成后）
  useEffect(() => {
    if (isNew && elementRef.current) {
      // 动画持续时间（与 CSS 保持一致）
      const timer = setTimeout(() => {
        if (elementRef.current) {
          elementRef.current.classList.remove('animate-in')
        }
      }, 600)
      return () => clearTimeout(timer)
    }
  }, [isNew])

  // 处理展开/收起，展开时加载详细数据
  const handleToggleExpanded = useCallback(async () => {
    const willBeExpanded = !isExpanded

    console.debug('[ActivityItem] 切换展开状态:', {
      activityId: activity.id,
      willBeExpanded,
      currentEventSummaries: activity.eventSummaries?.length ?? 0,
      isLoading
    })

    // 切换展开状态
    toggleExpanded(activity.id)

    // 如果展开，检查是否需要加载详细数据
    if (willBeExpanded && (!activity.eventSummaries || activity.eventSummaries.length === 0)) {
      console.debug('[ActivityItem] 活动展开，开始加载详细数据:', activity.id)
      try {
        await loadActivityDetails(activity.id)
        console.debug('[ActivityItem] 活动详细数据加载完成:', activity.id)
      } catch (error) {
        console.error('[ActivityItem] 加载活动详细数据失败:', error)
      }
    } else if (willBeExpanded) {
      console.debug('[ActivityItem] 活动已有事件数据，跳过加载:', activity.eventSummaries?.length)
    }
  }, [isExpanded, activity.id, activity.eventSummaries, toggleExpanded, loadActivityDetails, isLoading])

  // 处理分析活动：跳转到 Chat 页面并关联活动
  const handleAnalyzeActivity = useCallback(
    (e: MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation() // 防止触发展开/收起
      console.debug('[ActivityItem] 分析活动:', activity.id)
      // 跳转到 Chat 页面，通过 URL 参数传递活动 ID
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
      console.error('[ActivityItem] 删除活动失败:', error)
      toast.error(t('activity.deleteError') || 'Failed to delete activity')
    } finally {
      setIsDeleting(false)
      if (deletionSucceeded) {
        setDeleteDialogOpen(false)
      }
    }
  }, [activity.id, fetchActivityCountByDate, isDeleting, removeActivity, t])

  // 获取前1-2个事件用于预览
  const previewEvents = useMemo(() => {
    return sortedEventSummaries.slice(0, 2)
  }, [sortedEventSummaries])

  const hasMoreEvents = sortedEventSummaries.length > 2

  return (
    <div
      ref={elementRef}
      className={`relative pl-10 sm:pl-16 ${isNew ? 'animate-in fade-in slide-in-from-top-2 duration-500' : ''}`}>
      <div className="bg-border/50 absolute top-0 bottom-0 left-8 w-px -translate-x-1/2 transform" />
      <div className="bg-primary border-background shadow-primary/30 absolute top-4 left-8 h-3 w-3 -translate-x-1/2 transform rounded-full border-2 shadow-lg" />

      <div className="border-border/30 from-background/90 via-background/70 to-background/90 relative overflow-hidden rounded-3xl border bg-linear-to-br p-5 shadow-sm backdrop-blur">
        <div className="pointer-events-none absolute inset-0 opacity-80 [background:radial-gradient(circle_at_top,rgba(59,130,246,0.15),transparent_55%)]" />

        <div className="relative z-10 space-y-4">
          <div className="flex items-start gap-3">
            <button
              onClick={handleToggleExpanded}
              className="border-border/40 hover:border-primary/60 mt-0.5 rounded-full border p-1 transition">
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
                {sortedEventSummaries.length > 0 && (
                  <Badge variant="secondary" className="rounded-full px-3 text-[10px]">
                    {sortedEventSummaries.length} {t('activity.events')}
                  </Badge>
                )}
              </div>

              <div className="space-y-1">
                <h3 className="text-foreground text-lg font-semibold">{activity.title || t('activity.untitled')}</h3>
                {!isExpanded && activity.description && (
                  <p className="text-muted-foreground line-clamp-2 text-sm leading-relaxed">{activity.description}</p>
                )}
              </div>

              {!isExpanded && previewEvents.length > 0 && (
                <div className="border-border/40 bg-background/70 space-y-1 rounded-2xl border p-3 text-xs">
                  {previewEvents.map((summary) => (
                    <div key={summary.id} className="flex items-start gap-2">
                      <FileText className="text-primary/70 mt-0.5 h-3 w-3" />
                      <span className="text-muted-foreground line-clamp-1">{summary.title}</span>
                    </div>
                  ))}
                  {hasMoreEvents && (
                    <span className="text-primary text-xs font-medium">
                      +{sortedEventSummaries.length - 2} {t('activity.moreEvents')}
                    </span>
                  )}
                </div>
              )}
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
            <div className="bg-primary/5 border-primary/20 text-foreground rounded-2xl border p-4 text-sm leading-relaxed">
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
                <div className="border-border/40 text-muted-foreground flex items-center justify-center gap-2 rounded-2xl border border-dashed py-6 text-xs">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {t('common.loading')}
                </div>
              ) : sortedEventSummaries.length > 0 ? (
                <div className="relative pl-6">
                  <div className="from-primary/30 via-border absolute top-0 bottom-0 left-2 w-px bg-linear-to-b to-transparent" />
                  <div className="space-y-4">
                    {sortedEventSummaries.map((summary) => (
                      <div key={summary.id} className="relative">
                        <div className="bg-primary/70 border-background absolute top-2 left-0 h-2 w-2 -translate-x-3 rounded-full border-2" />
                        <EventSummaryItem summary={summary} />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-muted-foreground border-border/40 rounded-2xl border border-dashed py-6 text-center text-xs">
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
