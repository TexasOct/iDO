import { useEffect } from 'react'
import { useDashboardStore } from '@/lib/stores/dashboard'
import { useModelsStore } from '@/lib/stores/models'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { MetricCard } from '@/components/dashboard/metric-card'
import { BarChart, TrendingUp, Brain, DollarSign, Zap } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export default function DashboardView() {
  const { t } = useTranslation()
  // 分别订阅各个字段，避免选择器返回新对象
  const metrics = useDashboardStore((state) => state.metrics)
  const llmStats = useDashboardStore((state) => state.metrics.llmStats)
  const fetchMetrics = useDashboardStore((state) => state.fetchMetrics)
  const loading = useDashboardStore((state) => state.loading)
  const selectedModelId = useDashboardStore((state) => state.selectedModelId)
  const setSelectedModelId = useDashboardStore((state) => state.setSelectedModelId)

  const models = useModelsStore((state) => state.models)
  const fetchModels = useModelsStore((state) => state.fetchModels)
  const modelsLoading = useModelsStore((state) => state.loading)
  const isSingleModelView = selectedModelId !== 'all' && !!llmStats?.modelDetails

  useEffect(() => {
    fetchMetrics('day')
  }, [fetchMetrics])

  useEffect(() => {
    if (models.length === 0 && !modelsLoading) {
      fetchModels().catch((error) => {
        console.error('Failed to fetch models list for dashboard:', error)
      })
    }
  }, [models.length, modelsLoading, fetchModels])

  if (loading) {
    return <LoadingPage message={t('dashboard.loadingMetrics')} />
  }

  const priceUnit = t('dashboard.llmStats.modelPrice.perMillion')
  const inputLabel = t('dashboard.llmStats.modelPrice.inputLabel')
  const outputLabel = t('dashboard.llmStats.modelPrice.outputLabel')
  const formatPrice = (value?: number) => Number(value ?? 0).toFixed(2)

  const renderModelPriceCard = () => {
    if (!llmStats?.modelDetails) {
      return null
    }

    const { currency, inputTokenPrice, outputTokenPrice } = llmStats.modelDetails
    const inputPrice = formatPrice(inputTokenPrice)
    const outputPrice = formatPrice(outputTokenPrice)

    return (
      <MetricCard
        title={t('dashboard.llmStats.modelPrice.title')}
        icon={DollarSign}
        value={
          <div className="flex flex-col gap-3 text-left">
            {[
              { label: inputLabel, price: inputPrice },
              { label: outputLabel, price: outputPrice }
            ].map(({ label, price }) => (
              <div key={label} className="flex flex-col gap-1">
                <span className="text-muted-foreground text-xs font-medium uppercase">{label}</span>
                <span className="text-foreground text-base font-semibold">
                  {currency} {price}
                  <span className="text-muted-foreground text-xs"> · {priceUnit}</span>
                </span>
              </div>
            ))}
          </div>
        }
        valueClassName="text-left text-base font-normal"
        description={null}
        loading={loading}
      />
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <h1 className="text-2xl font-semibold">{t('dashboard.panelTitle')}</h1>
        <p className="text-muted-foreground mt-1 text-sm">{t('dashboard.description')}</p>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          {/* LLM 统计卡片区域 */}
          <div>
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-semibold">{t('dashboard.llmStats.title')}</h2>
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
                <span className="text-muted-foreground text-sm">{t('dashboard.llmStats.filterLabel')}</span>
                <Select
                  value={selectedModelId}
                  onValueChange={(value) => {
                    void setSelectedModelId(value)
                  }}
                  disabled={loading || modelsLoading}>
                  <SelectTrigger className="w-[220px]">
                    <SelectValue placeholder={t('dashboard.llmStats.selectPlaceholder')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t('dashboard.llmStats.allModels')}</SelectItem>
                    {models.map((model) => (
                      <SelectItem key={model.id} value={model.id}>
                        {model.name || model.model}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title={t('dashboard.llmStats.totalTokens.title')}
                value={llmStats?.totalTokens.toLocaleString() || '0'}
                icon={Brain}
                description={t('dashboard.llmStats.totalTokens.description')}
                loading={loading}
              />
              <MetricCard
                title={t('dashboard.llmStats.totalCalls.title')}
                value={llmStats?.totalCalls.toLocaleString() || '0'}
                icon={Zap}
                description={t('dashboard.llmStats.totalCalls.description')}
                loading={loading}
              />
              {isSingleModelView && (
                <MetricCard
                  title={t('dashboard.llmStats.totalCost.title')}
                  value={`${llmStats?.modelDetails?.currency || 'USD'} ${(llmStats?.totalCost ?? 0).toFixed(2)}`}
                  icon={DollarSign}
                  description={t('dashboard.llmStats.totalCost.description')}
                  loading={loading}
                />
              )}
              <MetricCard
                title={t('dashboard.llmStats.modelsUsed.title')}
                value={llmStats?.modelsUsed?.length || 0}
                icon={TrendingUp}
                description={`${t('dashboard.llmStats.modelsUsed.description')}: ${llmStats?.modelsUsed?.join(', ') || t('common.none', 'None')}`}
                loading={loading}
              />
              {isSingleModelView && renderModelPriceCard()}
            </div>
          </div>

          {/* 每日使用趋势 */}
          {llmStats?.dailyUsage && llmStats.dailyUsage.length > 0 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold">{t('dashboard.llmStats.dailyTrend.title')}</h2>
              <div className="grid gap-4 md:grid-cols-1">
                {llmStats.dailyUsage.slice(0, 7).map((day, index) => (
                  <div key={index} className="flex items-center justify-between rounded-lg border p-4">
                    <div className="flex items-center space-x-4">
                      <div className="h-2 w-2 rounded-full bg-blue-500"></div>
                      <span className="text-sm font-medium">{day.date}</span>
                    </div>
                    <div className="flex items-center space-x-6">
                      <div className="text-right">
                        <div className="text-sm font-medium">
                          {day.tokens.toLocaleString()} {t('dashboard.llmStats.dailyTrend.tokens')}
                        </div>
                        <div className="text-muted-foreground text-xs">
                          {day.calls} {t('dashboard.llmStats.dailyTrend.calls')}
                        </div>
                      </div>
                      {isSingleModelView && (
                        <div className="text-right">
                          <div className="text-sm font-medium">${day.cost.toFixed(2)}</div>
                          <div className="text-muted-foreground text-xs">{t('dashboard.llmStats.dailyTrend.cost')}</div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 临时占位内容 - 可在此处添加更多统计图表 */}
          {!llmStats && (
            <div className="text-muted-foreground flex flex-col items-center justify-center py-12">
              <BarChart className="mb-4 h-16 w-16" />
              <p className="text-lg font-medium">{t('dashboard.comingSoon')}</p>
              <p className="mt-2 text-sm">
                {t('dashboard.currentPeriod')}
                {metrics.period}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
