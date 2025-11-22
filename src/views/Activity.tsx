import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { toast } from 'sonner'
import { PageLayout } from '@/components/layout/PageLayout'
import { ActivityTimeline } from '@/components/activity/ActivityTimeline'
import { useActivityStore } from '@/lib/stores/activity'
import { Button } from '@/components/ui/button'

/**
 * Activity view with timeline list layout
 * Features:
 * - Timeline view with date grouping
 * - Category filtering (work, personal, distraction, idle)
 * - Activity statistics per day
 */
export default function ActivityView() {
  const { t } = useTranslation()
  const timelineData = useActivityStore((state) => state.timelineData)
  const loading = useActivityStore((state) => state.loading)
  const fetchTimelineData = useActivityStore((state) => state.fetchTimelineData)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)
  const [currentPage, setCurrentPage] = useState(0)
  const PAGE_SIZE = 1

  const totalPages = timelineData.length > 0 ? Math.ceil(timelineData.length / PAGE_SIZE) : 0
  const visibleDays = useMemo(() => {
    if (timelineData.length === 0) return []
    const startIndex = currentPage * PAGE_SIZE
    return timelineData.slice(startIndex, startIndex + PAGE_SIZE)
  }, [timelineData, currentPage, PAGE_SIZE])

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
    setCurrentPage(0)
  }, [timelineData.length])

  const handlePrevious = () => {
    if (totalPages === 0) return
    setCurrentPage((prev) => Math.min(prev + 1, totalPages - 1))
  }

  const handleNext = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 0))
  }

  return (
    <PageLayout>
      {/* Header */}
      <div className="border-border/40 border-b px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{t('activity.pageTitle')}</h1>
            <p className="text-muted-foreground mt-1 text-sm">{t('activity.description')}</p>
          </div>
          {totalPages > 0 && (
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handlePrevious}
                disabled={totalPages === 0 || currentPage >= totalPages - 1}
                className="h-9 gap-2">
                <ChevronLeft className="h-4 w-4" />
                <span className="text-xs tracking-widest uppercase">{t('activity.previousDay')}</span>
              </Button>
              <div className="text-muted-foreground text-sm">
                {currentPage + 1} / {totalPages}
              </div>
              <Button variant="ghost" size="sm" onClick={handleNext} disabled={currentPage === 0} className="h-9 gap-2">
                <span className="text-xs tracking-widest uppercase">{t('activity.nextDay')}</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Main Content: Timeline */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
          </div>
        ) : visibleDays.length > 0 ? (
          <ActivityTimeline data={visibleDays} />
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
