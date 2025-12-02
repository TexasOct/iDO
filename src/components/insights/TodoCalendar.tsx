import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'
import { todoDragEvents, type TodoDragTarget } from '@/lib/drag/todoDragController'
import { getDateLocale, formatDateString, isToday, isInMonth } from '@/lib/utils/date-i18n'

interface TodoCalendarProps {
  todos: InsightTodo[]
  selectedDate: string | null
  onDateSelect: (date: string) => void
  currentDate?: Date
}

export function TodoCalendar({
  todos,
  selectedDate,
  onDateSelect,
  currentDate: externalCurrentDate
}: TodoCalendarProps) {
  const { i18n } = useTranslation()
  const [internalCurrentDate] = useState(new Date())
  const currentDate = externalCurrentDate || internalCurrentDate
  // const setCurrentDate = externalCurrentDate ? () => {} : setInternalCurrentDate
  const [dragOverDate, setDragOverDate] = useState<string | null>(null)
  const calendarRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleTargetChange = (event: Event) => {
      const detail = (event as CustomEvent<TodoDragTarget | null>).detail
      if (detail?.view === 'month') {
        setDragOverDate(detail.date)
      } else {
        setDragOverDate(null)
      }
    }

    const handleDragEnd = () => setDragOverDate(null)

    window.addEventListener(todoDragEvents.TARGET_CHANGE_EVENT, handleTargetChange as EventListener)
    window.addEventListener(todoDragEvents.DRAG_END_EVENT, handleDragEnd)

    return () => {
      window.removeEventListener(todoDragEvents.TARGET_CHANGE_EVENT, handleTargetChange as EventListener)
      window.removeEventListener(todoDragEvents.DRAG_END_EVENT, handleDragEnd)
    }
  }, [])

  // Generate the calendar data for the current month
  const calendarDays = useMemo(() => {
    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()

    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)

    const startDate = new Date(firstDay)
    startDate.setDate(startDate.getDate() - firstDay.getDay())

    const endDate = new Date(lastDay)
    endDate.setDate(endDate.getDate() + (6 - lastDay.getDay()))

    const days: Date[] = []
    const current = new Date(startDate)

    while (current <= endDate) {
      days.push(new Date(current))
      current.setDate(current.getDate() + 1)
    }

    return days
  }, [currentDate])

  // Count tasks per day
  const todoCountByDate = useMemo(() => {
    const counts: Record<string, number> = {}
    todos.forEach((todo) => {
      if (todo.scheduledDate && !todo.completed) {
        counts[todo.scheduledDate] = (counts[todo.scheduledDate] || 0) + 1
      }
    })
    return counts
  }, [todos])

  // const goToPrevMonth = () => {
  //   setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1))
  // }

  // const goToNextMonth = () => {
  //   setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1))
  // }

  // const goToToday = () => {
  //   setCurrentDate(new Date())
  // }

  // const monthLabel = useMemo(() => {
  //   try {
  //     return new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long' }).format(currentDate)
  //   } catch {
  //     return `${currentDate.getFullYear()}-${currentDate.getMonth() + 1}`
  //   }
  // }, [currentDate, locale])

  const weekdayLabels = useMemo(() => {
    try {
      const dateLocale = getDateLocale(i18n.language)
      const baseDate = new Date(2021, 5, 6) // Sunday anchor
      return Array.from({ length: 7 }, (_, index) => {
        const date = new Date(baseDate)
        date.setDate(baseDate.getDate() + index)
        return format(date, 'EEE', { locale: dateLocale })
      })
    } catch {
      return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    }
  }, [i18n.language])

  return (
    <div ref={calendarRef} className="flex h-full flex-col">
      {/* Weekday headers */}
      <div className="grid grid-cols-7 border-b">
        {weekdayLabels.map((day) => (
          <div key={day} className="text-muted-foreground border-r p-2 text-center text-xs font-medium last:border-r-0">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="flex-1 overflow-auto">
        <div className="grid auto-rows-fr grid-cols-7">
          {calendarDays.map((date) => {
            const dateStr = formatDateString(date)
            const todoCount = todoCountByDate[dateStr] || 0
            const isSelected = selectedDate === dateStr
            const isDragOver = dragOverDate === dateStr

            return (
              <div
                key={dateStr}
                data-todo-dropzone="month"
                data-drop-date={dateStr}
                data-drop-key={`month-${dateStr}`}
                className={cn(
                  'relative min-h-20 border-r border-b p-2 transition-colors last:border-r-0',
                  'hover:bg-accent/50 cursor-pointer',
                  !isInMonth(date, currentDate) && 'bg-muted/30 text-muted-foreground',
                  isToday(date) && 'bg-primary/5',
                  isSelected && 'bg-accent ring-primary ring-2 ring-inset',
                  isDragOver && 'bg-primary/10 ring-primary dark:bg-primary/20 ring-2'
                )}
                onClick={() => onDateSelect(dateStr)}>
                <div className="pointer-events-none flex items-start justify-between">
                  <span
                    className={cn(
                      'text-sm',
                      isToday(date) && 'bg-primary text-primary-foreground rounded-full px-2 py-0.5 font-semibold'
                    )}>
                    {date.getDate()}
                  </span>
                  {todoCount > 0 && (
                    <span className="bg-primary text-primary-foreground rounded-full px-1.5 py-0.5 text-xs font-medium">
                      {todoCount}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
