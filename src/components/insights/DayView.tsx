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

  const getCurrentHour = (): number => {
    return new Date().getHours()
  }

  const dateStr = formatDate(currentDate)

  // Group todos by hour
  const todosByHour = useMemo(() => {
    const map: Record<number, InsightTodo[]> = {}
    todos.forEach((todo) => {
      if (!todo.scheduledDate || todo.completed || todo.scheduledDate !== dateStr) return

      // Extract hour from scheduledTime (format: "HH:MM" or "HH:MM:SS")
      let hour = 9 // default hour
      if (todo.scheduledTime) {
        const parts = todo.scheduledTime.split(':')
        hour = parseInt(parts[0], 10) || 9
      }

      if (!map[hour]) map[hour] = []
      map[hour].push(todo)
    })
    return map
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
        <div className="relative">
          {hours.map((hour) => {
            const cellTodos = todosByHour[hour] || []
            const isDragOver = dragOverHour === hour
            const isCurrentHour = isToday(currentDate) && hour === getCurrentHour()

            return (
              <div key={hour} className="flex border-b">
                {/* Time label */}
                <div className="text-muted-foreground w-20 shrink-0 border-r px-2 py-1 text-right text-sm">
                  {formatTime(hour)}
                </div>

                {/* Hour cell */}
                <div
                  className={cn(
                    'hover:bg-accent/50 relative min-h-20 flex-1 cursor-pointer p-2 transition-colors',
                    isDragOver && 'bg-blue-100 ring-2 ring-blue-400 ring-inset dark:bg-blue-950',
                    isCurrentHour && 'bg-primary/5'
                  )}
                  data-todo-dropzone="day"
                  data-drop-date={dateStr}
                  data-drop-time={formatTime(hour)}
                  data-drop-key={`day-${dateStr}-${hour}`}
                  onClick={() => onDateSelect(dateStr)}>
                  {/* Current time indicator */}
                  {isCurrentHour && <div className="bg-primary absolute top-0 right-0 left-0 h-0.5" />}

                  {/* Todos in this hour */}
                  <div className="space-y-1">
                    {cellTodos.map((todo) => (
                      <div
                        key={todo.id}
                        className="cursor-pointer rounded bg-blue-500 px-3 py-2 text-sm text-white hover:bg-blue-600"
                        title={`${todo.scheduledTime || ''} - ${todo.title}`}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <div className="font-medium">{todo.title}</div>
                            {todo.description && (
                              <div className="mt-1 line-clamp-2 text-xs text-blue-100">{todo.description}</div>
                            )}
                          </div>
                          {todo.scheduledTime && (
                            <div className="shrink-0 text-xs text-blue-100">{todo.scheduledTime}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
