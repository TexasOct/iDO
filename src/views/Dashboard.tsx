import { useEffect } from 'react'
import { useDashboardStore } from '@/lib/stores/dashboard'
import { useModelsStore } from '@/lib/stores/models'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { MetricCard } from '@/components/dashboard/metric-card'
import { UsageTrendChart } from '@/components/dashboard/usage-trend-chart'
import type { TrendDimension, TrendRange } from '@/lib/types/dashboard'
import { BarChart, TrendingUp, Brain, DollarSign, Zap } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'

export default function DashboardView() {
  const { t } = useTranslation()
  // 分别订阅各个字段，避免选择器返回新对象
  const metrics = useDashboardStore((state) => state.metrics)
  const llmStats = useDashboardStore((state) => state.metrics.llmStats)
  const fetchMetrics = useDashboardStore((state) => state.fetchMetrics)
  const loading = useDashboardStore((state) => state.loading)
  const selectedModelId = useDashboardStore((state) => state.selectedModelId)
  const setSelectedModelId = useDashboardStore((state) => state.setSelectedModelId)
  const trendDimension = useDashboardStore((state) => state.trendDimension)
  const trendRange = useDashboardStore((state) => state.trendRange)
  const trendData = useDashboardStore((state) => state.trendData)
  const trendLoading = useDashboardStore((state) => state.trendLoading)
  const setTrendDimension = useDashboardStore((state) => state.setTrendDimension)
  const setTrendRange = useDashboardStore((state) => state.setTrendRange)
  const fetchTrendData = useDashboardStore((state) => state.fetchTrendData)

  const models = useModelsStore((state) => state.models)
  const fetchModels = useModelsStore((state) => state.fetchModels)
  const modelsLoading = useModelsStore((state) => state.loading)
  const isSingleModelView = selectedModelId !== 'all' && !!llmStats?.modelDetails

  useEffect(() => {
    const {
      selectedModelId: initialModelId,
      trendDimension: initialDimension,
      trendRange: initialRange
    } = useDashboardStore.getState()
    fetchMetrics('day')
    const modelId = initialModelId === 'all' ? undefined : initialModelId
    fetchTrendData(initialDimension, initialRange, modelId).catch((error) => {
      console.error('Failed to fetch trend data:', error)
    })
  }, [fetchMetrics, fetchTrendData])

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
          <div className="flex flex-col gap-1 text-left text-sm">
            <div className="text-muted-foreground text-xs tracking-wide uppercase">{priceUnit}</div>
            <div className="grid gap-1">
              {[
                { label: inputLabel, price: inputPrice },
                { label: outputLabel, price: outputPrice }
              ].map(({ label, price }) => (
                <div key={label} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{label}</span>
                  <span className="text-foreground font-semibold">
                    {currency} {price}
                  </span>
                </div>
              ))}
            </div>
          </div>
        }
        valueClassName="text-left text-xs font-normal"
        description={null}
        loading={loading}
      />
    )
  }

  return (
    <PageLayout>
      <PageHeader title={t('dashboard.panelTitle')} description={t('dashboard.description')} />

      <div className="flex flex-1 flex-col gap-6 overflow-hidden px-6">
        <div className="flex-1 overflow-y-auto">
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
              <div className="flex flex-wrap justify-start gap-4">
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
                {!isSingleModelView && (
                  <MetricCard
                    title={t('dashboard.llmStats.modelsUsed.title')}
                    value={llmStats?.modelsUsed?.length || 0}
                    icon={TrendingUp}
                    description={`${t('dashboard.llmStats.modelsUsed.description')}: ${llmStats?.modelsUsed?.join(', ') || t('common.none', 'None')}`}
                    loading={loading}
                  />
                )}
                {isSingleModelView && renderModelPriceCard()}
              </div>
            </div>

            {/* 使用趋势图表 */}
            <UsageTrendChart
              data={trendData}
              dimension={trendDimension}
              range={trendRange}
              onDimensionChange={(dimension) => {
                setTrendDimension(dimension as TrendDimension).catch((error) => {
                  console.error('Failed to update trend dimension:', error)
                })
              }}
              onRangeChange={(range: TrendRange) => {
                setTrendRange(range).catch((error) => {
                  console.error('Failed to update trend range:', error)
                })
              }}
              loading={trendLoading}
            />

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
    </PageLayout>
  )
}
