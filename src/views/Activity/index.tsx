import { useEffect } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { EmptyState } from '@/components/shared/EmptyState'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { ActivityTimeline } from '@/components/activity/ActivityTimeline'
import { Clock, ExpandIcon, ShrinkIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'

export default function ActivityView() {
  const { t } = useTranslation()
  const { timelineData, fetchTimelineData, loading, expandAll, collapseAll } = useActivityStore()

  useEffect(() => {
    // 获取最近7天的数据
    const end = new Date()
    const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000)

    fetchTimelineData({
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0]
    })
  }, [fetchTimelineData])

  if (loading) {
    return <LoadingPage message={t('activity.loadingData')} />
  }

  if (timelineData.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6">
        <EmptyState icon={Clock} title={t('activity.noData')} description={t('activity.noDataDescription')} />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{t('activity.pageTitle')}</h1>
            <p className="text-sm text-muted-foreground mt-1">{t('activity.description')}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={expandAll}>
              <ExpandIcon className="h-4 w-4 mr-2" />
              {t('common.expandAll')}
            </Button>
            <Button variant="outline" size="sm" onClick={collapseAll}>
              <ShrinkIcon className="h-4 w-4 mr-2" />
              {t('common.collapseAll')}
            </Button>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <ActivityTimeline data={timelineData} />
      </div>
    </div>
  )
}
