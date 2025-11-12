import { useState, useMemo, useRef } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'

interface TodoCalendarProps {
  todos: InsightTodo[]
  selectedDate: string | null
  onDateSelect: (date: string) => void
  onDrop?: (todoId: string, date: string) => void
}

export function TodoCalendar({ todos, selectedDate, onDateSelect, onDrop }: TodoCalendarProps) {
  const { t, i18n } = useTranslation()
  const [currentDate, setCurrentDate] = useState(new Date())
  const [dragOverDate, setDragOverDate] = useState<string | null>(null)
  const calendarRef = useRef<HTMLDivElement>(null)
  const locale = i18n.language || 'en'

  // 使用鼠标事件处理拖放
  const handleMouseEnter = (date: Date) => {
    const draggingElement = document.querySelector('[data-dragging="true"]')
    if (draggingElement) {
      const dateStr = formatDate(date)
      console.log('Mouse enter date while dragging:', dateStr)
      setDragOverDate(dateStr)
    }
  }

  const handleMouseLeaveCalendar = () => {
    setDragOverDate(null)
  }

  const handleMouseUp = (date: Date) => {
    const draggingElement = document.querySelector('[data-dragging="true"]')
    if (draggingElement) {
      const todoId = draggingElement.getAttribute('data-todo-id')
      const dateStr = formatDate(date)
      console.log('Drop todo on date:', { todoId, date: dateStr })

      if (todoId && onDrop) {
        onDrop(todoId, dateStr)
      }

      // 清理拖拽状态
      draggingElement.removeAttribute('data-dragging')
      draggingElement.removeAttribute('data-todo-id')
      ;(draggingElement as HTMLElement).style.opacity = '1'
      setDragOverDate(null)
    }
  }

  // 生成当前月份的日历数据
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

  // 统计每天的任务数
  const todoCountByDate = useMemo(() => {
    const counts: Record<string, number> = {}
    todos.forEach((todo) => {
      if (todo.scheduledDate && !todo.completed) {
        counts[todo.scheduledDate] = (counts[todo.scheduledDate] || 0) + 1
      }
    })
    return counts
  }, [todos])

  const formatDate = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const goToPrevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1))
  }

  const goToNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1))
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  const isToday = (date: Date): boolean => {
    const today = new Date()
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    )
  }

  const isCurrentMonth = (date: Date): boolean => {
    return date.getMonth() === currentDate.getMonth()
  }

  const monthLabel = useMemo(() => {
    try {
      return new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long' }).format(currentDate)
    } catch {
      return `${currentDate.getFullYear()}-${currentDate.getMonth() + 1}`
    }
  }, [currentDate, locale])

  const weekdayLabels = useMemo(() => {
    try {
      const formatter = new Intl.DateTimeFormat(locale, { weekday: 'short' })
      const baseDate = new Date(2021, 5, 6) // Sunday anchor
      return Array.from({ length: 7 }, (_, index) => {
        const date = new Date(baseDate)
        date.setDate(baseDate.getDate() + index)
        return formatter.format(date)
      })
    } catch {
      return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    }
  }, [locale])

  return (
    <div ref={calendarRef} className="flex h-full flex-col" onMouseLeave={handleMouseLeaveCalendar}>
      {/* 月份导航 */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <Button variant="outline" size="sm" onClick={goToPrevMonth}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold">{monthLabel}</h3>
          <Button variant="outline" size="sm" onClick={goToToday}>
            {t('insights.calendarToday', 'Today')}
          </Button>
        </div>
        <Button variant="outline" size="sm" onClick={goToNextMonth}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* 星期标题 */}
      <div className="grid grid-cols-7 border-b">
        {weekdayLabels.map((day) => (
          <div key={day} className="text-muted-foreground border-r p-2 text-center text-xs font-medium last:border-r-0">
            {day}
          </div>
        ))}
      </div>

      {/* 日历网格 */}
      <div className="flex-1 overflow-auto">
        <div className="grid auto-rows-fr grid-cols-7">
          {calendarDays.map((date) => {
            const dateStr = formatDate(date)
            const todoCount = todoCountByDate[dateStr] || 0
            const isSelected = selectedDate === dateStr
            const isDragOver = dragOverDate === dateStr

            return (
              <div
                key={dateStr}
                className={cn(
                  'relative min-h-20 border-r border-b p-2 transition-colors last:border-r-0',
                  'hover:bg-accent/50 cursor-pointer',
                  !isCurrentMonth(date) && 'bg-muted/30 text-muted-foreground',
                  isToday(date) && 'bg-primary/5',
                  isSelected && 'bg-accent ring-primary ring-2 ring-inset',
                  isDragOver && 'bg-blue-100 ring-2 ring-blue-400 dark:bg-blue-950'
                )}
                onClick={() => onDateSelect(dateStr)}
                onMouseEnter={() => handleMouseEnter(date)}
                onMouseUp={() => handleMouseUp(date)}>
                <div className="pointer-events-none flex items-start justify-between">
                  <span
                    className={cn(
                      'text-sm',
                      isToday(date) && 'bg-primary text-primary-foreground rounded-full px-2 py-0.5 font-semibold'
                    )}>
                    {date.getDate()}
                  </span>
                  {todoCount > 0 && (
                    <span className="rounded-full bg-blue-500 px-1.5 py-0.5 text-xs font-medium text-white">
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
