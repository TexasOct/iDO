import { useTranslation } from 'react-i18next'
import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, XAxis, type TooltipProps } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChartConfig, ChartContainer, ChartTooltip } from '@/components/ui/chart'
import { BarChart3 } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import type { DateRange } from 'react-day-picker'
import { DatePicker } from '@/components/ui/date-picker'
import { TrendDataPoint, TrendDimension, TrendRange } from '@/lib/types/dashboard'
import { createCustomRange, createDayRange, createMonthRange, createWeekRange } from '@/lib/utils/date-range'

interface UsageTrendChartProps {
  data: TrendDataPoint[]
  dimension: TrendDimension
  range: TrendRange
  onDimensionChange: (dimension: TrendDimension) => void
  onRangeChange: (range: TrendRange) => void
  loading?: boolean
}

export function UsageTrendChart({
  data,
  dimension,
  range,
  onDimensionChange,
  onRangeChange,
  loading = false
}: UsageTrendChartProps) {
  const { t, i18n } = useTranslation()

  const preferredLocale =
    i18n.language?.replace('_', '-') || (typeof navigator !== 'undefined' ? navigator.language : 'en-US')
  const locale = preferredLocale || 'en-US'

  const parseDate = (value: string) => {
    const parsed = new Date(value)
    return Number.isNaN(parsed.getTime()) ? new Date() : parsed
  }

  const rangeStartDate = useMemo(() => parseDate(range.startDate), [range.startDate])
  const rangeEndDate = useMemo(() => parseDate(range.endDate), [range.endDate])

  const formatBucketLabel = (item: TrendDataPoint) => {
    const bucketStart = parseDate(item.bucketStart || item.date)
    if (dimension === 'day') {
      return bucketStart.toLocaleTimeString(locale, {
        hour: '2-digit',
        minute: '2-digit'
      })
    }
    return bucketStart.toLocaleDateString(locale, {
      month: 'short',
      day: 'numeric'
    })
  }

  const normalizedData = useMemo(() => {
    if (dimension !== 'week') {
      return data
    }

    const dayBuckets = new Map<string, TrendDataPoint>()

    data.forEach((item) => {
      const bucketStartDate = parseDate(item.bucketStart || item.date)
      const dayKey = `${bucketStartDate.getFullYear()}-${bucketStartDate.getMonth()}-${bucketStartDate.getDate()}`
      const existing = dayBuckets.get(dayKey)

      if (existing) {
        existing.promptTokens = (existing.promptTokens ?? 0) + (item.promptTokens ?? 0)
        existing.completionTokens = (existing.completionTokens ?? 0) + (item.completionTokens ?? 0)
        existing.tokens = (existing.tokens ?? 0) + (item.tokens ?? 0)
        existing.calls = (existing.calls ?? 0) + (item.calls ?? 0)
        existing.cost = (existing.cost ?? 0) + (item.cost ?? 0)
        if (item.bucketStart && (!existing.bucketStart || item.bucketStart < existing.bucketStart)) {
          existing.bucketStart = item.bucketStart
        }
        if (item.bucketEnd && (!existing.bucketEnd || item.bucketEnd > existing.bucketEnd)) {
          existing.bucketEnd = item.bucketEnd
        }
      } else {
        dayBuckets.set(dayKey, { ...item })
      }
    })

    return Array.from(dayBuckets.values()).sort((a, b) => {
      const aDate = parseDate(a.bucketStart || a.date)
      const bDate = parseDate(b.bucketStart || b.date)
      return aDate.getTime() - bDate.getTime()
    })
  }, [data, dimension])

  // Prepare chart data with formatted bucket labels
  const chartData = useMemo(() => {
    return normalizedData.map((item) => ({
      ...item,
      dateLabel: formatBucketLabel(item),
      inputTokens: item.promptTokens ?? 0,
      outputTokens: item.completionTokens ?? 0
    }))
  }, [normalizedData, dimension, locale])

  const today = new Date()
  const dimensionOptions: TrendDimension[] = ['day', 'week', 'month', 'custom']
  const [weekPickerOpen, setWeekPickerOpen] = useState(false)
  const [monthPickerOpen, setMonthPickerOpen] = useState(false)
  const [customPickerOpen, setCustomPickerOpen] = useState(false)
  const [customDraftRange, setCustomDraftRange] = useState<DateRange | undefined>()

  useEffect(() => {
    if (dimension === 'custom') {
      setCustomDraftRange({
        from: rangeStartDate,
        to: rangeEndDate
      })
    }
  }, [dimension, rangeStartDate, rangeEndDate])

  const getRangeLabel = (start: Date, end: Date) => {
    const formatter = new Intl.DateTimeFormat(locale, {
      month: 'short',
      day: 'numeric'
    })
    return `${formatter.format(start)} → ${formatter.format(end)}`
  }

  const weekButtonLabel = getRangeLabel(rangeStartDate, rangeEndDate)
  const monthButtonLabel = rangeStartDate.toLocaleDateString(locale, { month: 'long', year: 'numeric' })
  const customButtonLabel = getRangeLabel(rangeStartDate, rangeEndDate)

  const handleDaySelect = (date?: Date) => {
    if (!date) return
    onRangeChange(createDayRange(date))
  }

  const handleWeekSelect = (date?: Date) => {
    if (!date) return
    onRangeChange(createWeekRange(date))
    setWeekPickerOpen(false)
  }

  const handleMonthSelect = (date?: Date) => {
    if (!date) return
    onRangeChange(createMonthRange(date.getFullYear(), date.getMonth()))
    setMonthPickerOpen(false)
  }

  const handleCustomApply = () => {
    if (customDraftRange?.from && customDraftRange?.to) {
      onRangeChange(createCustomRange(customDraftRange.from, customDraftRange.to))
      setCustomPickerOpen(false)
    }
  }

  const pendingCustomDays =
    customDraftRange?.from && customDraftRange?.to
      ? Math.max(
          1,
          Math.floor((customDraftRange.to.getTime() - customDraftRange.from.getTime()) / (1000 * 60 * 60 * 24)) + 1
        )
      : 0

  const disableRangeControls = loading

  const renderRangeSelector = () => {
    if (dimension === 'day') {
      return (
        <DatePicker
          date={rangeStartDate}
          onDateChange={handleDaySelect}
          placeholder={t('dashboard.llmStats.trend.selector.dayPlaceholder')}
          maxDate={today}
          disabled={disableRangeControls}
          buttonSize="sm"
        />
      )
    }

    if (dimension === 'week') {
      return (
        <Popover open={weekPickerOpen} onOpenChange={setWeekPickerOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="font-normal" disabled={disableRangeControls}>
              {weekButtonLabel}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={rangeStartDate}
              onSelect={handleWeekSelect}
              disabled={{ after: today }}
              initialFocus
            />
            <div className="text-muted-foreground border-t px-3 py-2 text-xs">
              {t('dashboard.llmStats.trend.selector.weekHint')}
            </div>
          </PopoverContent>
        </Popover>
      )
    }

    if (dimension === 'month') {
      return (
        <Popover open={monthPickerOpen} onOpenChange={setMonthPickerOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="font-normal" disabled={disableRangeControls}>
              {monthButtonLabel}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={rangeStartDate}
              onSelect={handleMonthSelect}
              captionLayout="dropdown"
              disabled={{ after: today }}
              initialFocus
            />
            <div className="text-muted-foreground border-t px-3 py-2 text-xs">
              {t('dashboard.llmStats.trend.selector.monthHint')}
            </div>
          </PopoverContent>
        </Popover>
      )
    }

    const customHint = pendingCustomDays
      ? t('dashboard.llmStats.trend.selector.customDays', { count: pendingCustomDays })
      : t('dashboard.llmStats.trend.selector.customEmpty')

    return (
      <Popover open={customPickerOpen} onOpenChange={setCustomPickerOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm" className="font-normal" disabled={disableRangeControls}>
            {customButtonLabel}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="range"
            numberOfMonths={2}
            selected={customDraftRange}
            onSelect={setCustomDraftRange}
            disabled={{ after: today }}
            initialFocus
          />
          <div className="flex items-center justify-between border-t px-3 py-2">
            <div className="text-muted-foreground text-xs">{customHint}</div>
            <Button
              size="sm"
              onClick={handleCustomApply}
              disabled={disableRangeControls || !customDraftRange?.from || !customDraftRange?.to}
              className="text-xs">
              {t('dashboard.llmStats.trend.selector.apply')}
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    )
  }

  const chartConfig = {
    inputTokens: {
      label: t('dashboard.llmStats.trend.inputTokens'),
      color: '#2563eb'
    },
    outputTokens: {
      label: t('dashboard.llmStats.trend.outputTokens'),
      color: '#93c5fd'
    }
  } satisfies ChartConfig

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="text-primary h-4 w-4" aria-hidden />
            <CardTitle className="text-sm">{t('dashboard.llmStats.trend.title')}</CardTitle>
          </div>
          <div className="flex gap-1 rounded-md border p-1">
            {dimensionOptions.map((dim) => (
              <Button
                key={dim}
                variant={dimension === dim ? 'default' : 'ghost'}
                size="sm"
                onClick={() => onDimensionChange(dim)}
                className="h-7 px-3 text-xs">
                {t(`dashboard.llmStats.trend.dimension.${dim}`)}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-muted-foreground">{t('dashboard.llmStats.trend.selector.label')}</span>
          {renderRangeSelector()}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-muted-foreground flex h-40 items-center justify-center">{t('common.loading')}</div>
        ) : chartData.length === 0 ? (
          <div className="text-muted-foreground flex h-40 items-center justify-center">
            {t('dashboard.llmStats.trend.noData')}
          </div>
        ) : (
          <div className="w-full">
            <div className="h-[clamp(240px,40vh,360px)] w-full">
              <ChartContainer config={chartConfig} className="h-full w-full">
                <BarChart
                  accessibilityLayer
                  data={chartData}
                  margin={{
                    left: 12,
                    right: 12
                  }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="dateLabel" tickLine={false} axisLine={false} tickMargin={8} />
                  <ChartTooltip
                    cursor={false}
                    content={
                      <UsageTrendTooltip
                        chartConfig={chartConfig}
                        totalLabel={t('common.total', 'Total')}
                        unitLabel={t('dashboard.llmStats.trend.tokensLabel')}
                        dimension={dimension}
                        locale={locale}
                      />
                    }
                  />
                  <Bar dataKey="inputTokens" stackId="tokens" fill="var(--color-inputTokens)" radius={[0, 0, 4, 4]} />
                  <Bar dataKey="outputTokens" stackId="tokens" fill="var(--color-outputTokens)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ChartContainer>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

type UsageTrendTooltipProps = TooltipProps<number, string> & {
  chartConfig: ChartConfig
  totalLabel: string
  unitLabel: string
  dimension: TrendDimension
  locale: string
}

function UsageTrendTooltip({
  active,
  payload,
  chartConfig,
  totalLabel,
  unitLabel,
  dimension,
  locale
}: UsageTrendTooltipProps) {
  if (!active || !payload?.length) {
    return null
  }

  const total = payload.reduce((sum, item) => sum + Number(item.value ?? 0), 0)
  const bucketStart = payload[0]?.payload?.bucketStart as string | undefined
  const bucketEnd = payload[0]?.payload?.bucketEnd as string | undefined

  const formatTooltipTitle = () => {
    if (!bucketStart) {
      return ''
    }
    const start = new Date(bucketStart)
    const end = bucketEnd ? new Date(bucketEnd) : null
    const dateFormatter = new Intl.DateTimeFormat(locale, {
      month: 'short',
      day: 'numeric'
    })
    const timeFormatter = new Intl.DateTimeFormat(locale, {
      hour: '2-digit',
      minute: '2-digit'
    })

    if (dimension === 'day') {
      const startLabel = `${dateFormatter.format(start)} ${timeFormatter.format(start)}`
      const endLabel = end ? timeFormatter.format(end) : ''
      return `${startLabel} → ${endLabel}`
    }

    const dateLabel = start.toLocaleDateString(locale, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })

    if (dimension === 'week') {
      return dateLabel
    }

    return dateLabel
  }

  const headerLabel = formatTooltipTitle()

  return (
    <div className="bg-background/95 rounded-2xl border p-3 text-xs shadow-xl">
      <div className="space-y-2">
        {headerLabel && <div className="text-foreground font-medium">{headerLabel}</div>}
        {payload.map((item) => {
          const key = String(item.dataKey ?? item.name)
          const color =
            (item.payload?.fill as string | undefined) || (item.color as string | undefined) || `var(--color-${key})`
          const label = chartConfig[key as keyof typeof chartConfig]?.label ?? key
          const value = Number(item.value ?? 0).toLocaleString()

          return (
            <div key={key} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: color }} aria-hidden />
                <span className="text-foreground">{label}</span>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-foreground font-semibold">{value}</span>
                <span className="text-muted-foreground text-[11px]">{unitLabel}</span>
              </div>
            </div>
          )
        })}
        <div className="border-t pt-2">
          <div className="flex items-center justify-between">
            <span className="text-foreground font-medium">{totalLabel}</span>
            <div className="flex items-baseline gap-1">
              <span className="text-foreground font-semibold">{total.toLocaleString()}</span>
              <span className="text-muted-foreground text-[11px]">{unitLabel}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
