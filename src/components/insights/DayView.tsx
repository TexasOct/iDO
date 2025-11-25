import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'
import { todoDragEvents, type TodoDragTarget } from '@/lib/drag/todoDragController'

interface DayViewProps {
  currentDate: Date
  todos: InsightTodo[]
  selectedDate: string | null
  onDateSelect: (date: string) => void
}

// Height of each hour in pixels
const HOUR_HEIGHT = 80

// Parse time string (HH:MM) to minutes since midnight
function timeToMinutes(timeStr: string): number {
  const [hours, minutes] = timeStr.split(':').map((n) => parseInt(n, 10))
  return hours * 60 + (minutes || 0)
}

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
    console.log('[DayView] Todo:', todo.title, 'Start:', startTime, 'End:', endTime, 'EndTime type:', typeof endTime)
  }

  const startMinutes = timeToMinutes(startTime)

  // If no end time or empty string, default to 1 hour duration
  const endMinutes = endTime && endTime.trim() ? timeToMinutes(endTime) : startMinutes + 60

  // Calculate pixel positions (HOUR_HEIGHT pixels per hour = HOUR_HEIGHT/60 pixels per minute)
  const pixelsPerMinute = HOUR_HEIGHT / 60
  const top = startMinutes * pixelsPerMinute
  const height = Math.max((endMinutes - startMinutes) * pixelsPerMinute, 20) // Minimum 20px

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

export function DayView({ currentDate, todos, onDateSelect }: DayViewProps) {
  const { t, i18n } = useTranslation()
  const locale = i18n.language || 'en'
  const [dragOverHour, setDragOverHour] = useState<number | null>(null)

  // Generate hours (0-23)
  const hours = useMemo(() => Array.from({ length: 24 }, (_, i) => i), [])

  const formatDate = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const formatTime = (hour: number): string => {
    return `${String(hour).padStart(2, '0')}:00`
  }

  const isToday = (date: Date): boolean => {
    const today = new Date()
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    )
  }

  const getCurrentTimePosition = (): number => {
    const now = new Date()
    const minutes = now.getHours() * 60 + now.getMinutes()
    return (minutes * HOUR_HEIGHT) / 60
  }

  const dateStr = formatDate(currentDate)

  // Process todos for this date with positions
  const positionedTodos = useMemo(() => {
    return todos
      .filter((todo) => !todo.completed && todo.scheduledDate === dateStr)
      .map((todo) => ({
        todo,
        position: calculateTodoPosition(todo)
      }))
      .filter((item) => item.position !== null) as Array<{ todo: InsightTodo; position: TodoPosition }>
  }, [todos, dateStr])

  useEffect(() => {
    const handleTargetChange = (event: Event) => {
      const detail = (event as CustomEvent<TodoDragTarget | null>).detail
      if (detail?.view === 'day' && detail.date === dateStr && detail.time) {
        const hour = parseInt(detail.time.split(':')[0], 10)
        if (!Number.isNaN(hour)) {
          setDragOverHour(hour)
          return
        }
      }
      setDragOverHour(null)
    }

    const clearHighlight = () => setDragOverHour(null)

    window.addEventListener(todoDragEvents.TARGET_CHANGE_EVENT, handleTargetChange as EventListener)
    window.addEventListener(todoDragEvents.DRAG_END_EVENT, clearHighlight)

    return () => {
      window.removeEventListener(todoDragEvents.TARGET_CHANGE_EVENT, handleTargetChange as EventListener)
      window.removeEventListener(todoDragEvents.DRAG_END_EVENT, clearHighlight)
    }
  }, [dateStr])

  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long'
      }),
    [locale]
  )

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header with date */}
      <div className="shrink-0 border-b p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">{dateFormatter.format(currentDate)}</h2>
            {isToday(currentDate) && <p className="text-primary text-sm font-medium">{t('insights.calendarToday')}</p>}
          </div>
        </div>
      </div>

      {/* Time grid */}
      <div className="flex-1 overflow-x-hidden overflow-y-auto">
        <div className="flex">
          {/* Time labels column */}
          <div className="w-20 shrink-0">
            {hours.map((hour) => (
              <div
                key={hour}
                className="text-muted-foreground border-b px-2 py-1 text-right text-sm"
                style={{ height: `${HOUR_HEIGHT}px` }}>
                {formatTime(hour)}
              </div>
            ))}
          </div>

          {/* Main content area with todos */}
          <div className="relative flex-1 border-l">
            {/* Hour grid background */}
            {hours.map((hour) => {
              const isDragOver = dragOverHour === hour
              return (
                <div
                  key={hour}
                  className={cn(
                    'hover:bg-accent/30 border-b transition-colors',
                    isDragOver && 'bg-primary/10 ring-primary dark:bg-primary/20 ring-2 ring-inset'
                  )}
                  style={{ height: `${HOUR_HEIGHT}px` }}
                  data-todo-dropzone="day"
                  data-drop-date={dateStr}
                  data-drop-time={formatTime(hour)}
                  data-drop-key={`day-${dateStr}-${hour}`}
                />
              )
            })}

            {/* Current time indicator */}
            {isToday(currentDate) && (
              <div
                className="bg-primary pointer-events-none absolute right-0 left-0 z-10 h-0.5"
                style={{ top: `${getCurrentTimePosition()}px` }}>
                <div className="bg-primary absolute -top-1.5 -left-1.5 size-3 rounded-full" />
              </div>
            )}

            {/* Positioned todos - pointer-events-none to allow dropzone detection */}
            <div className="pointer-events-none absolute inset-0 px-2">
              {positionedTodos.map(({ todo, position }) => (
                <div
                  key={todo.id}
                  className="pointer-events-auto absolute right-2 left-2 cursor-pointer"
                  style={{
                    top: `${position.top}px`,
                    height: `${position.height}px`,
                    zIndex: 5
                  }}
                  onClick={(e) => {
                    e.stopPropagation()
                    onDateSelect(dateStr)
                  }}>
                  <div className="bg-primary text-primary-foreground hover:bg-primary/90 flex h-full flex-col overflow-hidden rounded-lg px-3 py-2 shadow-sm transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 overflow-hidden">
                        <div className="truncate font-medium">{todo.title}</div>
                        {position.height > 40 && todo.description && (
                          <div className="text-primary-foreground/80 mt-1 line-clamp-2 text-xs">{todo.description}</div>
                        )}
                      </div>
                      <div className="text-primary-foreground/90 shrink-0 text-xs font-medium">
                        {position.startTime}
                        {position.endTime !== position.startTime && ` - ${position.endTime}`}
                      </div>
                    </div>

                    {/* Duration indicator for long events */}
                    {position.height > 60 && (
                      <div className="text-primary-foreground/70 mt-auto pt-1 text-xs">
                        {Math.round(position.height / (HOUR_HEIGHT / 60))} min
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
