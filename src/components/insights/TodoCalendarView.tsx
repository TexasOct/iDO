import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { format } from 'date-fns'
import { Button } from '@/components/ui/button'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import { TodoCalendar } from './TodoCalendar'
import { WeekView } from './WeekView'
import { DayView } from './DayView'
import type { InsightTodo } from '@/lib/services/insights'
import { getDateLocale, getDateFormat } from '@/lib/utils/date-i18n'

type ViewMode = 'day' | 'week' | 'month' | 'year'

interface TodoCalendarViewProps {
  todos: InsightTodo[]
  selectedDate: string | null
  onDateSelect: (date: string) => void
}

export function TodoCalendarView({ todos, selectedDate, onDateSelect }: TodoCalendarViewProps) {
  const { t, i18n } = useTranslation()
  const [viewMode, setViewMode] = useState<ViewMode>('week')
  const [currentDate, setCurrentDate] = useState(new Date())

  const goToPrev = () => {
    const newDate = new Date(currentDate)
    switch (viewMode) {
      case 'day':
        newDate.setDate(newDate.getDate() - 1)
        break
      case 'week':
        newDate.setDate(newDate.getDate() - 7)
        break
      case 'month':
        newDate.setMonth(newDate.getMonth() - 1)
        break
      case 'year':
        newDate.setFullYear(newDate.getFullYear() - 1)
        break
    }
    setCurrentDate(newDate)
  }

  const goToNext = () => {
    const newDate = new Date(currentDate)
    switch (viewMode) {
      case 'day':
        newDate.setDate(newDate.getDate() + 1)
        break
      case 'week':
        newDate.setDate(newDate.getDate() + 7)
        break
      case 'month':
        newDate.setMonth(newDate.getMonth() + 1)
        break
      case 'year':
        newDate.setFullYear(newDate.getFullYear() + 1)
        break
    }
    setCurrentDate(newDate)
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  const getTitle = () => {
    const locale = getDateLocale(i18n.language)
    switch (viewMode) {
      case 'day':
        return format(currentDate, getDateFormat(i18n.language, 'full'), { locale })
      case 'week':
      case 'month':
        return format(currentDate, getDateFormat(i18n.language, 'month'), { locale })
      case 'year':
        return format(currentDate, getDateFormat(i18n.language, 'year'), { locale })
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header with view switcher */}
      <div className="flex shrink-0 items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={goToPrev}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={goToNext}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={goToToday}>
            {t('insights.calendarToday')}
          </Button>
          <h2 className="ml-4 text-lg font-semibold">{getTitle()}</h2>
        </div>

        <div className="flex items-center gap-1">
          <Button variant={viewMode === 'day' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('day')}>
            {t('insights.calendarViewDay')}
          </Button>
          <Button variant={viewMode === 'week' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('week')}>
            {t('insights.calendarViewWeek')}
          </Button>
          <Button variant={viewMode === 'month' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('month')}>
            {t('insights.calendarViewMonth')}
          </Button>
          <Button variant={viewMode === 'year' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('year')}>
            {t('insights.calendarViewYear')}
          </Button>
        </div>
      </div>

      {/* Calendar content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'day' && (
          <DayView currentDate={currentDate} todos={todos} selectedDate={selectedDate} onDateSelect={onDateSelect} />
        )}
        {viewMode === 'week' && (
          <WeekView currentDate={currentDate} todos={todos} selectedDate={selectedDate} onDateSelect={onDateSelect} />
        )}
        {viewMode === 'month' && (
          <TodoCalendar
            currentDate={currentDate}
            todos={todos}
            selectedDate={selectedDate}
            onDateSelect={onDateSelect}
          />
        )}
        {viewMode === 'year' && (
          <div className="flex h-full items-center justify-center">
            <div className="text-muted-foreground text-center">
              <Calendar className="mx-auto mb-4 h-12 w-12" />
              <p>{t('insights.calendarYearViewComingSoon')}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
