import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { Loader2, RefreshCw, Sparkles } from 'lucide-react'
import { useInsightsStore } from '@/lib/stores/insights'
import { DiaryCard } from '@/components/insights/DiaryCard'
import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'

const dateToISO = (date: Date) => date.toISOString().slice(0, 10)

export default function AIDiaryView() {
  const { t } = useTranslation()
  const diaries = useInsightsStore((state) => state.diaries)
  const loading = useInsightsStore((state) => state.loadingDiaries)
  const refreshDiaries = useInsightsStore((state) => state.refreshDiaries)
  const removeDiary = useInsightsStore((state) => state.removeDiary)
  const createDiary = useInsightsStore((state) => state.createDiaryForDate)
  const lastError = useInsightsStore((state) => state.lastError)
  const clearError = useInsightsStore((state) => state.clearError)

  const [limit, setLimit] = useState(10)
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())

  useEffect(() => {
    void refreshDiaries(limit)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!lastError) return
    toast.error(lastError)
    clearError()
  }, [lastError, clearError])

  const handleRefresh = () => {
    void refreshDiaries(limit)
  }

  const handleLoadMore = () => {
    const nextLimit = limit + 10
    setLimit(nextLimit)
    void refreshDiaries(nextLimit)
  }

  const handleGenerate = async () => {
    try {
      const dateToGenerate = dateToISO(selectedDate)
      await createDiary(dateToGenerate)
      toast.success(t('insights.generateDiarySuccess'))
      void refreshDiaries(limit)
    } catch (error) {
      toast.error((error as Error).message)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await removeDiary(id)
      toast.success(t('insights.deleteSuccess'))
    } catch (error) {
      toast.error((error as Error).message)
    }
  }

  const hasMore = useMemo(() => diaries.length >= limit, [diaries.length, limit])

  return (
    <PageLayout>
      <PageHeader title={t('insights.diarySummary')} description={t('insights.diaryPageDescription')} />

      <div className="flex flex-1 flex-col gap-6 overflow-hidden">
        <div className="flex flex-wrap items-center gap-3 px-6">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            {t('common.refresh')}
          </Button>
          {hasMore && (
            <Button variant="ghost" size="sm" onClick={handleLoadMore} disabled={loading}>
              {t('insights.loadMoreDiaries')}
            </Button>
          )}
          <DatePicker
            date={selectedDate}
            onDateChange={(date) => date && setSelectedDate(date)}
            placeholder={t('insights.selectDate') || 'Select date'}
            disabled={loading}
            buttonSize="sm"
          />
          <Button size="sm" onClick={handleGenerate} disabled={loading} className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            {t('insights.generateDiaryButton')}
          </Button>
        </div>

        {loading && diaries.length === 0 ? (
          <div className="border-muted/60 rounded-2xl p-10">
            <div className="flex items-center justify-center gap-2 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>{t('insights.loading')}</span>
            </div>
          </div>
        ) : diaries.length === 0 ? (
          <div className="border-muted/60 rounded-2xl p-10 text-center">
            <p className="text-muted-foreground text-sm">{t('insights.noDiaries')}</p>
          </div>
        ) : (
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6">
            {diaries.map((diary) => (
              <DiaryCard key={diary.id} diary={diary} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </PageLayout>
  )
}
