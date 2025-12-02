import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'
import { todoDragEvents, type TodoDragTarget } from '@/lib/drag/todoDragController'
import { getDateLocale, formatDateString, formatTime, isToday, timeToMinutes } from '@/lib/utils/date-i18n'

interface WeekViewProps {
  currentDate: Date
  todos: InsightTodo[]
  selectedDate: string | null
  onDateSelect: (date: string) => void
}

// Height of each hour in pixels
const HOUR_HEIGHT = 64

// Calculate position and height for a todo based on its time range
interface TodoPosition {
  top: number // pixels from midnight
  height: number // pixels
  startTime: string
  endTime: string
}

function calculateTodoPosition(todo: InsightTodo): TodoPosition | null {
  const startTime = todo.scheduledTime || '09:00'
  const endTime = todo.scheduledEndTime

  // Debug log
  if (todo.title && endTime) {
    console.log('[WeekView] Todo:', todo.title, 'Start:', startTime, 'End:', endTime, 'EndTime type:', typeof endTime)
  }

  const startMinutes = timeToMinutes(startTime)

  // If no end time or empty string, default to 1 hour duration
  const endMinutes = endTime && endTime.trim() ? timeToMinutes(endTime) : startMinutes + 60

  // Calculate pixel positions
  const pixelsPerMinute = HOUR_HEIGHT / 60
  const top = startMinutes * pixelsPerMinute
  const height = Math.max((endMinutes - startMinutes) * pixelsPerMinute, 16) // Minimum 16px

  return {
    top,
    height,
    startTime,
    endTime:
      endTime && endTime.trim()
        ? endTime
        : `${String(Math.floor(endMinutes / 60)).padStart(2, '0')}:${String(endMinutes % 60).padStart(2, '0')}`
  }
}

export function WeekView({ currentDate, todos, selectedDate, onDateSelect }: WeekViewProps) {
  const { i18n } = useTranslation()
  const [dragOverCell, setDragOverCell] = useState<{ date: string; hour: number } | null>(null)

  // Generate hours (0-23)
  const hours = useMemo(() => Array.from({ length: 24 }, (_, i) => i), [])

  // Get the week days starting from Sunday
  const weekDays = useMemo(() => {
    const start = new Date(currentDate)
    // Get to the start of the week (Sunday)
    const day = start.getDay()
    start.setDate(start.getDate() - day)

    const days: Date[] = []
    for (let i = 0; i < 7; i++) {
      const date = new Date(start)
      date.setDate(start.getDate() + i)
      days.push(date)
    }
    return days
  }, [currentDate])

  const getCurrentTimePosition = (): number => {
    const now = new Date()
    const minutes = now.getHours() * 60 + now.getMinutes()
    return (minutes * HOUR_HEIGHT) / 60
  }

  // Process todos by date with positions
  const todosByDate = useMemo(() => {
    const map: Record<string, Array<{ todo: InsightTodo; position: TodoPosition }>> = {}

    todos.forEach((todo) => {
      if (!todo.scheduledDate || todo.completed) return

      const position = calculateTodoPosition(todo)
      if (!position) return

      const date = todo.scheduledDate
      if (!map[date]) map[date] = []
      map[date].push({ todo, position })
    })

    return map
  }, [todos])

  useEffect(() => {
    const handleTargetChange = (event: Event) => {
      const detail = (event as CustomEvent<TodoDragTarget | null>).detail
      if (detail?.view === 'week' && detail.date) {
        const hour = detail.time ? parseInt(detail.time.split(':')[0], 10) : null
        if (hour !== null && !Number.isNaN(hour)) {
          setDragOverCell({ date: detail.date, hour })
        } else {
          setDragOverCell(null)
        }
      } else {
        setDragOverCell(null)
      }
    }

    const clearHighlight = () => setDragOverCell(null)

    window.addEventListener(todoDragEvents.TARGET_CHANGE_EVENT, handleTargetChange as EventListener)
    window.addEventListener(todoDragEvents.DRAG_END_EVENT, clearHighlight)

    return () => {
      window.removeEventListener(todoDragEvents.TARGET_CHANGE_EVENT, handleTargetChange as EventListener)
      window.removeEventListener(todoDragEvents.DRAG_END_EVENT, clearHighlight)
    }
  }, [])

  const dateLocale = useMemo(() => getDateLocale(i18n.language), [i18n.language])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header with days */}
      <div className="flex shrink-0 border-b">
        {/* Empty cell for time column */}
        <div className="w-16 shrink-0 border-r" />
        {/* Day headers grid */}
        <div className="grid flex-1 grid-cols-7">
          {weekDays.map((date) => {
            const dateStr = formatDateString(date)
            const isSelectedDate = selectedDate === dateStr
            const dayTodos = todosByDate[dateStr] || []
            const todoCount = dayTodos.length

            return (
              <div
                key={dateStr}
                className={cn(
                  'relative border-r p-2 text-center last:border-r-0',
                  isToday(date) && 'bg-primary/10',
                  isSelectedDate && 'bg-accent'
                )}>
                <div className="text-muted-foreground text-xs">{format(date, 'EEE', { locale: dateLocale })}</div>
                <div className="flex items-center justify-center gap-1">
                  <div
                    className={cn(
                      'mt-1 text-lg font-semibold',
                      isToday(date) && 'bg-primary text-primary-foreground inline-block rounded-full px-2'
                    )}>
                    {date.getDate()}
                  </div>
                  {todoCount > 0 && (
                    <div className="bg-primary text-primary-foreground mt-1 flex size-5 items-center justify-center rounded-full text-[10px] font-medium">
                      {todoCount}
                    </div>
                  )}
                </div>
                <div className="text-muted-foreground text-[10px]">{format(date, 'MMM', { locale: dateLocale })}</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Time grid */}
      <div className="flex-1 overflow-x-hidden overflow-y-auto">
        <div className="flex">
          {/* Time labels column */}
          <div className="w-16 shrink-0 border-r">
            {hours.map((hour) => (
              <div
                key={hour}
                className="text-muted-foreground border-b px-2 py-1 text-right text-xs"
                style={{ height: `${HOUR_HEIGHT}px` }}>
                {formatTime(hour)}
              </div>
            ))}
          </div>

          {/* Day columns with todos */}
          <div className="grid flex-1 grid-cols-7">
            {weekDays.map((date, index) => {
              const dateStr = formatDateString(date)
              const isSelectedDate = selectedDate === dateStr
              const dayTodos = todosByDate[dateStr] || []
              const isLastDay = index === weekDays.length - 1

              return (
                <div key={dateStr} className={cn('relative border-r', isLastDay && 'border-r-0')}>
                  {/* Hour grid background */}
                  {hours.map((hour) => {
                    const isDragOver = dragOverCell?.date === dateStr && dragOverCell?.hour === hour
                    return (
                      <div
                        key={hour}
                        className={cn(
                          'hover:bg-accent/30 border-b transition-colors',
                          isSelectedDate && 'bg-accent/20',
                          isDragOver && 'bg-primary/10 ring-primary dark:bg-primary/20 ring-2 ring-inset'
                        )}
                        style={{ height: `${HOUR_HEIGHT}px` }}
                        data-todo-dropzone="week"
                        data-drop-date={dateStr}
                        data-drop-time={formatTime(hour)}
                        data-drop-key={`week-${dateStr}-${hour}`}
                        onClick={() => onDateSelect(dateStr)}
                      />
                    )
                  })}

                  {/* Current time indicator */}
                  {isToday(date) && (
                    <div
                      className="bg-primary pointer-events-none absolute right-0 left-0 z-10 h-0.5"
                      style={{ top: `${getCurrentTimePosition()}px` }}
                    />
                  )}

                  {/* Positioned todos - pointer-events-none to allow dropzone detection */}
                  <div className="pointer-events-none absolute inset-0 px-1">
                    {dayTodos.map(({ todo, position }) => {
                      const durationMinutes = timeToMinutes(position.endTime) - timeToMinutes(position.startTime)
                      const durationHours = Math.floor(durationMinutes / 60)
                      const durationMins = durationMinutes % 60
                      const durationText =
                        durationHours > 0
                          ? durationMins > 0
                            ? `${durationHours}h ${durationMins}m`
                            : `${durationHours}h`
                          : `${durationMins}m`

                      return (
                        <div
                          key={todo.id}
                          className="pointer-events-auto absolute right-1 left-1 cursor-pointer"
                          style={{
                            top: `${position.top}px`,
                            height: `${position.height}px`,
                            zIndex: 5
                          }}
                          onClick={(e) => {
                            e.stopPropagation()
                            onDateSelect(dateStr)
                          }}>
                          <div
                            className="bg-primary text-primary-foreground hover:bg-primary/90 flex h-full flex-col overflow-hidden rounded px-1.5 py-1 text-xs shadow-sm transition-colors"
                            title={`${todo.title}\n${position.startTime} - ${position.endTime} (${durationText})`}>
                            {/* Title - always show */}
                            <div className="truncate leading-tight font-medium">{todo.title}</div>

                            {/* Time range - show for medium+ height */}
                            {position.height > 24 && (
                              <div className="text-primary-foreground/90 mt-0.5 truncate text-[10px] font-medium">
                                {position.startTime} - {position.endTime}
                              </div>
                            )}

                            {/* Duration badge - show for larger height */}
                            {position.height > 48 && (
                              <div className="bg-primary-foreground/20 mt-auto inline-block self-start rounded px-1 py-0.5 text-[9px] font-medium">
                                {durationText}
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
