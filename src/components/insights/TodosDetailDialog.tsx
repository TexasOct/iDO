import { useEffect, useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Label } from '@/components/ui/label'
import { DatePicker } from '@/components/ui/date-picker'
import { TimeRangeEditor } from './TimeRangeEditor'
import { InsightTodo, RecurrenceRule } from '@/lib/services/insights'
import { ChevronLeft, ChevronRight, Check, Calendar, Trash2 } from 'lucide-react'

interface TodosDetailDialogProps {
  todos: InsightTodo[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onComplete?: (todo: InsightTodo) => void
  onDelete?: (todo: InsightTodo) => void
  onUnschedule?: (todo: InsightTodo) => void
  onUpdateSchedule?: (
    todo: InsightTodo,
    scheduledDate: string,
    scheduledTime?: string,
    scheduledEndTime?: string,
    recurrenceRule?: RecurrenceRule
  ) => void
}

export function TodosDetailDialog({
  todos,
  open,
  onOpenChange,
  onComplete,
  onDelete,
  onUnschedule,
  onUpdateSchedule
}: TodosDetailDialogProps) {
  const { t, i18n } = useTranslation()
  const [currentIndex, setCurrentIndex] = useState(0)

  // Sort todos by time (earliest first) for intuitive navigation
  // Left arrow = earlier, Right arrow = later
  const sortedTodos = useMemo(() => {
    return [...todos].sort((a, b) => {
      // If no scheduled time, sort to end
      if (!a.scheduledTime) return 1
      if (!b.scheduledTime) return -1

      // Compare times (HH:MM format)
      return a.scheduledTime.localeCompare(b.scheduledTime)
    })
  }, [todos])

  // Current todo from sorted list
  const currentTodo = sortedTodos[currentIndex]
  const hasPrevious = currentIndex > 0
  const hasNext = currentIndex < sortedTodos.length - 1
  const isScheduled = !!currentTodo?.scheduledDate

  // Time range state
  const [startTime, setStartTime] = useState(currentTodo?.scheduledTime || '09:00')
  const [endTime, setEndTime] = useState(currentTodo?.scheduledEndTime ?? '')
  const [recurrenceRule, setRecurrenceRule] = useState<RecurrenceRule>(currentTodo?.recurrenceRule || { type: 'none' })
  const [selectedDate, setSelectedDate] = useState(currentTodo?.scheduledDate || '')

  // Sync state when currentTodo changes
  useEffect(() => {
    if (currentTodo) {
      const start = currentTodo.scheduledTime || '09:00'
      const end = currentTodo.scheduledEndTime ?? ''
      console.log('[TodosDetailDialog] Syncing state:', {
        title: currentTodo.title,
        scheduledTime: currentTodo.scheduledTime,
        scheduledEndTime: currentTodo.scheduledEndTime,
        endTimeType: typeof currentTodo.scheduledEndTime,
        willSetEndTimeTo: end,
        isUndefined: currentTodo.scheduledEndTime === undefined,
        scheduledDate: currentTodo.scheduledDate
      })
      setStartTime(start)
      setEndTime(end)
      setRecurrenceRule(currentTodo.recurrenceRule || { type: 'none' })
      setSelectedDate(currentTodo.scheduledDate || '')
    }
  }, [currentTodo])

  // Reset index when dialog opens (only when open state changes from false to true)
  useEffect(() => {
    if (open) {
      setCurrentIndex(0)
      console.log('[TodosDetailDialog] Dialog opened, reset to first todo')
    }
  }, [open])

  // Navigation handlers
  const handlePrevious = () => {
    if (hasPrevious) {
      setCurrentIndex(currentIndex - 1)
    }
  }

  const handleNext = () => {
    if (hasNext) {
      setCurrentIndex(currentIndex + 1)
    }
  }

  // Helper function to calculate end time (1 hour after start time)
  const calculateEndTime = (start: string): string => {
    const [hours, minutes] = start.split(':').map(Number)
    const endHour = (hours + 1) % 24
    return `${String(endHour).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
  }

  // Action handlers
  const handleSaveSchedule = () => {
    if (currentTodo) {
      // Use selectedDate if available, otherwise fall back to currentTodo.scheduledDate
      const dateToSchedule = selectedDate || currentTodo.scheduledDate

      if (!dateToSchedule) {
        console.error('[TodosDetailDialog] No date selected for scheduling')
        return
      }

      const finalStartTime = startTime || '09:00'
      // If no end time provided, default to 1 hour after start time
      const finalEndTime = endTime && endTime.trim() ? endTime : calculateEndTime(finalStartTime)

      console.log('[TodosDetailDialog] Saving schedule:', {
        title: currentTodo.title,
        startTime,
        endTime,
        finalStartTime,
        finalEndTime,
        hasEndTime: !!(endTime && endTime.trim()),
        recurrenceRule,
        dateToSchedule,
        isFirstTimeScheduling: !currentTodo.scheduledDate
      })
      onUpdateSchedule?.(currentTodo, dateToSchedule, finalStartTime, finalEndTime, recurrenceRule)
    }
  }

  const handleComplete = () => {
    if (currentTodo) {
      onComplete?.(currentTodo)
      // If there are more todos, move to next
      if (hasNext) {
        handleNext()
      } else if (hasPrevious) {
        handlePrevious()
      } else {
        // Last todo, close dialog
        onOpenChange(false)
      }
    }
  }

  const handleDelete = () => {
    if (currentTodo) {
      onDelete?.(currentTodo)
      // If there are more todos, stay at current index or move to previous
      if (hasNext) {
        // Stay at current index (next todo will take its place)
      } else if (hasPrevious) {
        handlePrevious()
      } else {
        // Last todo, close dialog
        onOpenChange(false)
      }
    }
  }

  const handleUnschedule = () => {
    if (currentTodo) {
      onUnschedule?.(currentTodo)
      onOpenChange(false)
    }
  }

  if (!currentTodo) {
    return null
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-2xl">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex-1">{t('insights.todoDetails')}</DialogTitle>

            {/* Navigation Controls */}
            {sortedTodos.length > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handlePrevious}
                  disabled={!hasPrevious}
                  className="size-8"
                  title={t('common.previous', 'Previous')}>
                  <ChevronLeft className="size-4" />
                </Button>

                <span className="text-muted-foreground text-sm">
                  {currentIndex + 1} / {sortedTodos.length}
                </span>

                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleNext}
                  disabled={!hasNext}
                  className="size-8"
                  title={t('common.next', 'Next')}>
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            )}
          </div>

          <DialogDescription>
            {isScheduled ? (
              <span className="flex items-center gap-1 text-xs">
                <Calendar className="size-3" />
                {currentTodo.scheduledDate}
                {currentTodo.scheduledTime && (
                  <>
                    <span className="text-muted-foreground mx-1">·</span>
                    <span className="font-mono">
                      {currentTodo.scheduledTime}
                      {currentTodo.scheduledEndTime && ` - ${currentTodo.scheduledEndTime}`}
                    </span>
                  </>
                )}
              </span>
            ) : (
              <span className="text-muted-foreground text-xs">
                {t('insights.unscheduledTodo', 'This todo has not been scheduled yet')}
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[calc(85vh-200px)]">
          <div className="space-y-4">
            {/* Todo Title */}
            <div>
              <h3 className="text-lg font-semibold">{currentTodo.title}</h3>
              {currentTodo.type === 'combined' && currentTodo.mergedFromIds && (
                <Badge variant="secondary" className="mt-1 text-xs">
                  {t('insights.mergedFrom')} {currentTodo.mergedFromIds.length} {t('insights.todosCount')}
                </Badge>
              )}
            </div>

            {/* Todo Description */}
            <div>
              <p className="text-muted-foreground text-sm whitespace-pre-wrap">{currentTodo.description}</p>
            </div>

            {/* Keywords */}
            {currentTodo.keywords && currentTodo.keywords.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {currentTodo.keywords.map((keyword, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    {keyword}
                  </Badge>
                ))}
              </div>
            )}

            <Separator />

            {/* Schedule Section */}
            <div className="space-y-4 pb-4">
              {/* Date Selector - always show for scheduling */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">{t('insights.scheduleDate', 'Schedule Date')}</Label>
                <DatePicker
                  value={selectedDate}
                  onChange={setSelectedDate}
                  placeholder={t('insights.selectDate', 'Select a date')}
                  locale={i18n.language}
                />
                {!isScheduled && selectedDate && (
                  <p className="text-muted-foreground text-xs">
                    {t('insights.scheduleHint', 'Set the date and time, then click "Schedule" to save')}
                  </p>
                )}
              </div>

              {/* Time Range Editor - show when date is selected */}
              {selectedDate && (
                <TimeRangeEditor
                  startTime={startTime}
                  endTime={endTime}
                  recurrenceRule={recurrenceRule}
                  onStartTimeChange={setStartTime}
                  onEndTimeChange={setEndTime}
                  onRecurrenceChange={setRecurrenceRule}
                />
              )}
            </div>
          </div>
        </ScrollArea>

        <DialogFooter className="gap-2">
          {/* Unschedule Button - only show for already scheduled todos */}
          {isScheduled && (
            <Button variant="outline" size="sm" onClick={handleUnschedule} className="mr-auto">
              <Calendar className="mr-2 size-4" />
              {t('insights.unschedule')}
            </Button>
          )}

          {/* Delete Button */}
          <Button variant="destructive" size="sm" onClick={handleDelete}>
            <Trash2 className="mr-2 size-4" />
            {t('insights.delete')}
          </Button>

          {/* Complete Button */}
          <Button variant="default" size="sm" onClick={handleComplete}>
            <Check className="mr-2 size-4" />
            {t('insights.markComplete')}
          </Button>

          {/* Schedule/Save Schedule Button - show when date is selected */}
          {selectedDate && (
            <Button variant="default" size="sm" onClick={handleSaveSchedule}>
              <Calendar className="mr-2 size-4" />
              {isScheduled ? t('insights.saveSchedule') : t('insights.schedule', 'Schedule')}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
