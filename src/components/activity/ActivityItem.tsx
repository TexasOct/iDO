import { Activity } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChevronDown, ChevronRight, Clock, Loader2, MessageSquare, Sparkles, Trash2 } from 'lucide-react'
import { format } from 'date-fns'
import { EventSummaryItem } from './EventSummaryItem'
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
    if (!activity.eventSummaries) return []
    return [...activity.eventSummaries].sort((a, b) => b.timestamp - a.timestamp)
  }, [activity.eventSummaries])

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

    // 切换展开状态
    toggleExpanded(activity.id)

    // 如果展开，检查是否需要加载详细数据
    if (willBeExpanded && (!activity.eventSummaries || activity.eventSummaries.length === 0)) {
      console.debug('[ActivityItem] 活动展开，加载详细数据:', activity.id)
      await loadActivityDetails(activity.id)
    }
  }, [isExpanded, activity.id, activity.eventSummaries, toggleExpanded, loadActivityDetails])

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

  return (
    <div ref={elementRef} className={isNew ? 'animate-in fade-in slide-in-from-top-2 duration-500' : ''}>
      <Card>
        <CardHeader className="py-3">
          <div className="group flex w-full items-start gap-2">
            <button onClick={handleToggleExpanded} className="mt-0.5 flex-shrink-0">
              {isLoading ? (
                <Loader2 className="text-muted-foreground h-4 w-4 animate-spin" />
              ) : isExpanded ? (
                <ChevronDown className="text-muted-foreground h-4 w-4" />
              ) : (
                <ChevronRight className="text-muted-foreground h-4 w-4" />
              )}
            </button>
            <div onClick={handleToggleExpanded} className="min-w-0 flex-1 cursor-pointer">
              <div className="flex items-center gap-2">
                <CardTitle className="group-hover:text-primary text-base transition-colors">{activity.title}</CardTitle>
              </div>
              <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
                <Clock className="h-3 w-3" />
                <span>{time}</span>
              </div>
            </div>
            {/* 分析按钮 */}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleAnalyzeActivity}
              className="ml-2 h-8 px-2"
              title={t('activity.analyzeInChat')}>
              <MessageSquare className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDeleteButtonClick}
              className="text-destructive hover:text-destructive ml-1 h-8 px-2"
              title={t('activity.deleteActivity')}
              disabled={isDeleting}>
              {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            </Button>
          </div>
        </CardHeader>

        {isExpanded && (
          <CardContent className="space-y-2 pt-0">
            {/* 显示完整描述 */}
            {activity.description && (
              <div className="mb-3 flex items-start gap-3">
                <Sparkles className="text-primary mt-0.5 h-4 w-4 flex-shrink-0" />
                <p className="text-foreground/80 text-sm leading-relaxed whitespace-pre-wrap">{activity.description}</p>
              </div>
            )}
            {/* 事件摘要 */}
            {isLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="text-muted-foreground mr-2 h-4 w-4 animate-spin" />
                <span className="text-muted-foreground text-sm">{t('common.loading')}</span>
              </div>
            ) : sortedEventSummaries.length > 0 ? (
              sortedEventSummaries.map((summary) => <EventSummaryItem key={summary.id} summary={summary} />)
            ) : (
              <div className="text-muted-foreground py-4 text-center text-sm">{t('activity.noEventSummaries')}</div>
            )}
          </CardContent>
        )}
      </Card>

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
