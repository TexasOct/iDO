import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DatePicker } from '@/components/ui/date-picker'
import { Loader2, RefreshCw, Trash2, Sparkles } from 'lucide-react'
import { useInsightsStore } from '@/lib/stores/insights'
import DiaryContent from '@/components/shared/DiaryContent'

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
    <div className="flex h-full flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t('insights.diarySummary')}</h1>
        <p className="text-muted-foreground text-sm">{t('insights.diaryPageDescription')}</p>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            {t('common.refresh')}
          </Button>
          {hasMore && (
            <Button variant="ghost" size="sm" onClick={handleLoadMore} disabled={loading}>
              {t('insights.loadMoreDiaries')}
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <DatePicker
            date={selectedDate}
            onDateChange={(date) => date && setSelectedDate(date)}
            placeholder={t('insights.selectDate') || 'Select date'}
            disabled={loading}
          />
          <Button size="sm" onClick={handleGenerate} disabled={loading} className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            {t('insights.generateDiaryButton')}
          </Button>
        </div>
      </div>

      {loading && diaries.length === 0 ? (
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('insights.loading')}
        </div>
      ) : diaries.length === 0 ? (
        <div className="border-muted/60 rounded-2xl border border-dashed p-10 text-center">
          <p className="text-muted-foreground text-sm">{t('insights.noDiaries')}</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {diaries.map((diary) => (
            <Card key={diary.id} className="shadow-sm">
              <CardHeader>
                <div className="flex items-start gap-3">
                  <div className="flex-1">
                    <CardTitle className="text-lg leading-tight">{diary.date}</CardTitle>
                    <CardDescription className="text-muted-foreground mt-1 text-xs">
                      {diary.createdAt ? new Date(diary.createdAt).toLocaleString() : null}
                    </CardDescription>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(diary.id)} className="h-8 w-8">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <DiaryContent text={diary.content} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
