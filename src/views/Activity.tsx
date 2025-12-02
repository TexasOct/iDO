import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react'
import { toast } from 'sonner'
import { PageLayout } from '@/components/layout/PageLayout'
import { ActivityTimeline } from '@/components/activity/ActivityTimeline'
import { useActivityStore } from '@/lib/stores/activity'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/layout/PageHeader'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { fetchActivityTimeline } from '@/lib/services/activity/db'
import { TimelineDay } from '@/lib/types/activity'
import { format, parseISO } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'

/**
 * Activity view with timeline list layout
 * Features:
 * - Timeline view with date grouping
 * - Category filtering (work, personal, distraction, idle)
 * - Activity statistics per day
 */
export default function ActivityView() {
  const { t, i18n } = useTranslation()
  const timelineData = useActivityStore((state) => state.timelineData)
  const loading = useActivityStore((state) => state.loading)
  const fetchTimelineData = useActivityStore((state) => state.fetchTimelineData)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)
  const selectedDate = useActivityStore((state) => state.selectedDate)
  const setSelectedDate = useActivityStore((state) => state.setSelectedDate)
  const dateCountMap = useActivityStore((state) => state.dateCountMap)
  const cacheVersion = useActivityStore((state) => state.cacheVersion)
  const [calendarOpen, setCalendarOpen] = useState(false)
  const [extraDays, setExtraDays] = useState<Record<string, TimelineDay>>({})
  const [dateLoading, setDateLoading] = useState(false)

  const availableDates = useMemo(() => {
    const dateSet = new Set<string>()
    timelineData.forEach((day) => dateSet.add(day.date))
    Object.keys(dateCountMap).forEach((date) => dateSet.add(date))
    return Array.from(dateSet).sort((a, b) => (a > b ? -1 : 1))
  }, [timelineData, dateCountMap])

  const availableDateSet = useMemo(() => new Set(availableDates), [availableDates])

  const selectedDayFromTimeline = useMemo(() => {
    if (!selectedDate) return null
    return timelineData.find((day) => day.date === selectedDate) ?? null
  }, [selectedDate, timelineData])

  const selectedDayFromCache = selectedDate ? (extraDays[selectedDate] ?? null) : null
  const displayedDay = selectedDayFromTimeline ?? selectedDayFromCache ?? null

  const selectedDateLabel = useMemo(() => {
    if (!selectedDate) return ''
    try {
      const parsed = parseISO(selectedDate)
      // Use date-fns locale for better i18n support
      const locale = i18n.language.startsWith('zh') ? zhCN : enUS
      // Format: "November 23, 2025, Sunday" for en or "2025-11-23 Sunday" for zh
      const formattedDate = format(parsed, 'PPP, EEEE', { locale })
      return formattedDate
    } catch (error) {
      console.warn('[ActivityView] Failed to format date label', error)
      return selectedDate
    }
  }, [selectedDate, i18n.language])

  const totalDates = availableDates.length
  const currentIndex = selectedDate ? availableDates.indexOf(selectedDate) : -1
  const previousDisabled = currentIndex === -1 || currentIndex >= totalDates - 1
  const nextDisabled = currentIndex <= 0

  // Load timeline data on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        await fetchTimelineData({ limit: 100 })
        await fetchActivityCountByDate()
      } catch (error) {
        console.error('[ActivityView] Failed to load activities:', error)
        toast.error(t('activity.loadingData'))
      }
    }

    void loadData()
  }, [fetchTimelineData, fetchActivityCountByDate, t])

  useEffect(() => {
    if (!selectedDate && timelineData.length > 0) {
      setSelectedDate(timelineData[0].date)
    }
  }, [selectedDate, timelineData, setSelectedDate])

  useEffect(() => {
    if (!selectedDate && availableDates.length > 0) {
      setSelectedDate(availableDates[0])
    }
  }, [selectedDate, availableDates, setSelectedDate])

  useEffect(() => {
    setExtraDays({})
  }, [cacheVersion])

  useEffect(() => {
    if (!selectedDate) {
      setDateLoading(false)
      return
    }

    if (selectedDayFromTimeline || extraDays[selectedDate]) {
      setDateLoading(false)
      return
    }

    let cancelled = false
    setDateLoading(true)

    const loadDay = async () => {
      try {
        const result = await fetchActivityTimeline({ start: selectedDate, end: selectedDate, limit: 50 })
        if (cancelled) return
        const day = result[0] ?? { date: selectedDate, activities: [] }
        setExtraDays((prev) => ({ ...prev, [selectedDate]: day }))
      } catch (error) {
        if (!cancelled) {
          console.error(`[ActivityView] Failed to load activities for ${selectedDate}:`, error)
          toast.error(t('activity.dateLoadError'))
        }
      } finally {
        if (!cancelled) {
          setDateLoading(false)
        }
      }
    }

    void loadDay()

    return () => {
      cancelled = true
    }
  }, [selectedDate, selectedDayFromTimeline, extraDays, cacheVersion, t])

  const handlePrevious = () => {
    if (previousDisabled || currentIndex === -1) return
    const prevDate = availableDates[currentIndex + 1]
    if (prevDate) {
      setSelectedDate(prevDate)
    }
  }

  const handleNext = () => {
    if (nextDisabled || currentIndex === -1) return
    const nextDate = availableDates[currentIndex - 1]
    if (nextDate) {
      setSelectedDate(nextDate)
    }
  }

  const handleDateSelect = (value?: Date) => {
    if (!value) return
    const normalized = format(value, 'yyyy-MM-dd')
    if (!availableDateSet.has(normalized)) return
    setSelectedDate(normalized)
    setCalendarOpen(false)
  }

  const calendarDisabledMatcher =
    availableDateSet.size === 0
      ? undefined
      : (date: Date) => {
          const normalized = format(date, 'yyyy-MM-dd')
          return !availableDateSet.has(normalized)
        }

  const isLoading = loading || dateLoading

  return (
    <PageLayout>
      {/* Header */}
      <PageHeader
        title={t('activity.pageTitle')}
        description={t('activity.description')}
        actions={
          totalDates > 0 && (
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={handlePrevious}
                disabled={previousDisabled}
                className="h-10 gap-2 px-4">
                <ChevronLeft className="h-4 w-4" />
                <span className="text-xs font-medium tracking-wider uppercase">{t('activity.previousDay')}</span>
              </Button>
              <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm" className="h-10 min-w-72 justify-between px-4">
                    <div className="flex flex-col items-start gap-0.5">
                      <span className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">
                        {t('activity.dateSelectorLabel')}
                      </span>
                      <span className="text-sm leading-tight font-medium">
                        {selectedDate ? selectedDateLabel : t('activity.dateSelectorPlaceholder')}
                      </span>
                    </div>
                    <CalendarIcon className="text-muted-foreground ml-2 h-4 w-4 shrink-0" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="end">
                  <div className="p-3">
                    <Calendar
                      mode="single"
                      selected={selectedDate ? parseISO(selectedDate) : undefined}
                      onSelect={handleDateSelect}
                      disabled={calendarDisabledMatcher}
                      locale={i18n.language.startsWith('zh') ? zhCN : enUS}
                      autoFocus
                    />
                    <p className="text-muted-foreground mt-2 text-xs">{t('activity.dateSelectorHelper')}</p>
                    <div className="text-muted-foreground mt-1 text-right text-xs">
                      {currentIndex >= 0 ? `${currentIndex + 1} / ${totalDates}` : `0 / ${totalDates}`}
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleNext}
                disabled={nextDisabled}
                className="h-10 gap-2 px-4">
                <span className="text-xs font-medium tracking-wider uppercase">{t('activity.nextDay')}</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )
        }
      />

      {/* Main Content: Timeline */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
          </div>
        ) : displayedDay ? (
          <ActivityTimeline data={[displayedDay]} />
        ) : (
          <div className="text-muted-foreground flex h-full flex-col items-center justify-center text-center">
            <h3 className="text-foreground mb-2 text-lg font-semibold">{t('activity.noData')}</h3>
            <p className="text-sm leading-relaxed">{t('activity.noDataDescription')}</p>
          </div>
        )}
      </div>
    </PageLayout>
  )
}
