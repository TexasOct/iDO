import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'

import { cn } from '@/lib/utils'
import { useSystemStatus } from '@/hooks/useSystemStatus'

interface SystemStatusIndicatorProps {
  compact?: boolean
}

export function SystemStatusIndicator({ compact = false }: SystemStatusIndicatorProps) {
  const { t } = useTranslation()
  const { status, message, loading, activeModel } = useSystemStatus()

  const { colorClass, statusText } = useMemo(() => {
    if (loading) {
      return {
        colorClass: 'bg-muted-foreground/60 animate-pulse',
        statusText: t('system.status.detecting')
      }
    }

    switch (status) {
      case 'running':
        return {
          colorClass: 'bg-emerald-500',
          statusText: t('system.status.running')
        }
      case 'limited':
        return {
          colorClass: 'bg-red-500',
          statusText: t('system.status.limited')
        }
      case 'stopped':
        return {
          colorClass: 'bg-red-500',
          statusText: t('system.status.stopped')
        }
      case 'error':
        return {
          colorClass: 'bg-red-500',
          statusText: t('system.status.error')
        }
      default:
        return {
          colorClass: 'bg-muted-foreground/60',
          statusText: t('system.status.detecting')
        }
    }
  }, [loading, status, t])

  const formatTimestamp = (value?: string | null) => {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
      return value
    }
    return date.toLocaleString()
  }

  const detail = useMemo(() => {
    if (loading) {
      return t('system.status.detecting')
    }
    if (status === 'running') {
      const formatted = formatTimestamp(activeModel?.lastTestedAt)
      if (formatted) {
        return t('system.test.lastSuccess', { time: formatted })
      }
      return null
    }
    if (status === 'limited') {
      if (activeModel?.lastTestStatus === false) {
        const formatted = formatTimestamp(activeModel.lastTestedAt)
        if (formatted) {
          return t('system.test.lastFailure', {
            time: formatted,
            reason: activeModel.lastTestError || t('system.test.unknownReason')
          })
        }
        return activeModel.lastTestError || t('system.messages.modelNotTested') || ''
      }
      return message
    }
    return message
  }, [activeModel, loading, message, status, t])

  const tooltipParts = [statusText]
  if (activeModel?.name) {
    tooltipParts.push(activeModel.name)
  }
  if (detail) {
    tooltipParts.push(detail)
  } else if (message) {
    tooltipParts.push(message)
  }
  const tooltip = tooltipParts.filter(Boolean).join(' · ')

  if (compact) {
    return (
      <div className="flex items-center justify-center" title={tooltip || undefined}>
        <span className={cn('inline-flex h-2.5 w-2.5 rounded-full', colorClass)} />
        <span className="sr-only">
          {t('system.statusLabel')}: {statusText}
        </span>
      </div>
    )
  }

  return (
    <div
      className="bg-background/90 text-muted-foreground border-border/80 flex items-center gap-2 rounded-full border px-3 py-2 text-xs shadow-sm backdrop-blur"
      title={tooltip || undefined}>
      <span className={cn('inline-flex h-2.5 w-2.5 shrink-0 rounded-full', colorClass)} />
      <div className="flex min-w-0 flex-col">
        <span className="text-foreground text-xs leading-tight font-semibold">{t('system.statusLabel')}</span>
        <span className="text-foreground text-xs leading-tight">{statusText}</span>
        {detail ? <span className="text-muted-foreground text-[11px] leading-tight">{detail}</span> : null}
      </div>
    </div>
  )
}
