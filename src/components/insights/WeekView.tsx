import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'
import { todoDragEvents, type TodoDragTarget } from '@/lib/drag/todoDragController'

interface WeekViewProps {
  currentDate: Date
  todos: InsightTodo[]
  selectedDate: string | null
  onDateSelect: (date: string) => void
}

export function WeekView({ currentDate, todos, selectedDate, onDateSelect }: WeekViewProps) {
  const { i18n } = useTranslation()
  const locale = i18n.language || 'en'
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

  // Group todos by date and hour
  const todosByDateAndHour = useMemo(() => {
    const map: Record<string, Record<number, InsightTodo[]>> = {}
    todos.forEach((todo) => {
      if (!todo.scheduledDate || todo.completed) return

      const date = todo.scheduledDate
      // Extract hour from scheduledTime (format: "HH:MM" or "HH:MM:SS")
      let hour = 9 // default hour
      if (todo.scheduledTime) {
        const parts = todo.scheduledTime.split(':')
        hour = parseInt(parts[0], 10) || 9
      }

      if (!map[date]) map[date] = {}
      if (!map[date][hour]) map[date][hour] = []
      map[date][hour].push(todo)
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

  const weekdayFormatter = useMemo(() => new Intl.DateTimeFormat(locale, { weekday: 'short' }), [locale])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header with days */}
      <div className="grid shrink-0 grid-cols-8 border-b">
        {/* Empty cell for time column */}
        <div className="border-r p-2" />
        {weekDays.map((date) => {
          const dateStr = formatDate(date)
          const isSelectedDate = selectedDate === dateStr
          return (
            <div
              key={dateStr}
              className={cn(
                'border-r p-2 text-center last:border-r-0',
                isToday(date) && 'bg-primary/10',
                isSelectedDate && 'bg-accent'
              )}>
              <div className="text-muted-foreground text-xs">{weekdayFormatter.format(date)}</div>
              <div
                className={cn(
                  'mt-1 text-lg font-semibold',
                  isToday(date) && 'bg-primary text-primary-foreground inline-block rounded-full px-2'
                )}>
                {date.getDate()}
              </div>
            </div>
          )
        })}
      </div>

      {/* Time grid */}
      <div className="flex-1 overflow-x-hidden overflow-y-auto">
        <div className="relative">
          {hours.map((hour) => (
            <div key={hour} className="grid grid-cols-8 border-b">
              {/* Time label */}
              <div className="text-muted-foreground border-r px-2 py-1 text-right text-xs">{formatTime(hour)}</div>

              {/* Day cells */}
              {weekDays.map((date) => {
                const dateStr = formatDate(date)
                const isSelectedDate = selectedDate === dateStr
                const isDragOver = dragOverCell?.date === dateStr && dragOverCell?.hour === hour
                const cellTodos = todosByDateAndHour[dateStr]?.[hour] || []
                const isCurrentHour = isToday(date) && hour === getCurrentHour()

                return (
                  <div
                    key={`${dateStr}-${hour}`}
                    data-todo-dropzone="week"
                    data-drop-date={dateStr}
                    data-drop-time={formatTime(hour)}
                    data-drop-key={`week-${dateStr}-${hour}`}
                    className={cn(
                      'relative min-h-16 border-r p-1 transition-colors last:border-r-0',
                      'hover:bg-accent/50 cursor-pointer',
                      isSelectedDate && 'bg-accent/30',
                      isDragOver && 'bg-blue-100 ring-2 ring-blue-400 ring-inset dark:bg-blue-950',
                      isCurrentHour && 'bg-primary/5'
                    )}
                    onClick={() => onDateSelect(dateStr)}>
                    {/* Current time indicator */}
                    {isCurrentHour && <div className="bg-primary absolute top-0 right-0 left-0 h-0.5" />}

                    {/* Todos in this cell */}
                    {cellTodos.map((todo) => (
                      <div
                        key={todo.id}
                        className="mb-1 cursor-pointer truncate rounded bg-blue-500 px-1.5 py-0.5 text-xs text-white hover:bg-blue-600"
                        title={todo.title}>
                        {todo.title}
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
