import { useEffect } from 'react'
import { useDashboardStore } from '@/lib/stores/dashboard'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { BarChart } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function DashboardView() {
  const { t } = useTranslation()
  const { metrics, fetchMetrics, loading } = useDashboardStore()

  useEffect(() => {
    fetchMetrics('day')
  }, [fetchMetrics])

  if (loading) {
    return <LoadingPage message={t('dashboard.loadingMetrics')} />
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <h1 className="text-2xl font-semibold">{t('dashboard.panelTitle')}</h1>
        <p className="text-muted-foreground mt-1 text-sm">{t('dashboard.description')}</p>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <div className="text-muted-foreground flex h-full flex-col items-center justify-center">
          <BarChart className="mb-4 h-16 w-16" />
          <p className="text-lg font-medium">{t('dashboard.comingSoon')}</p>
          <p className="mt-2 text-sm">
            {t('dashboard.currentPeriod')}
            {metrics.period}
          </p>
        </div>
      </div>
    </div>
  )
}
