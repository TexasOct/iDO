import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ReactNode } from 'react'

interface MetricCardProps {
  title: string
  value: ReactNode
  icon: LucideIcon
  description?: ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  className?: string
  loading?: boolean
  valueClassName?: string
}

export function MetricCard({
  title,
  value,
  icon: Icon,
  description,
  trend,
  className,
  loading,
  valueClassName
}: MetricCardProps) {
  if (loading) {
    return (
      <Card className={cn('relative max-w-60 overflow-hidden', className)}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <Icon className="text-muted-foreground h-4 w-4" />
        </CardHeader>
        <CardContent>
          <div className="bg-muted h-8 w-24 animate-pulse rounded" />
        </CardContent>
      </Card>
    )
  }

  const renderDescription = () => {
    if (!description) {
      return null
    }

    if (typeof description === 'string') {
      return <p className="text-muted-foreground mt-1 text-xs">{description}</p>
    }

    return <div className="text-muted-foreground mt-1 text-xs">{description}</div>
  }

  return (
    <Card className={cn('relative w-45 overflow-hidden', className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1.5">
        <CardTitle className="text-xs font-medium">{title}</CardTitle>
        <Icon className="text-muted-foreground h-3.5 w-3.5" />
      </CardHeader>
      <CardContent className="pt-1">
        <div className={cn(valueClassName ?? 'text-xl font-bold')}>{value}</div>
        {description !== null && renderDescription()}
        {trend && (
          <div className="mt-1.5 flex items-center">
            <span className={cn('text-xs font-medium', trend.isPositive ? 'text-green-600' : 'text-red-600')}>
              {trend.isPositive ? '+' : ''}
              {trend.value}%
            </span>
            <span className="text-muted-foreground ml-1 text-xs">vs last period</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
