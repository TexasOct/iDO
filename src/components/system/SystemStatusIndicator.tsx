import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { Settings, Activity, AlertCircle } from 'lucide-react'

import { cn } from '@/lib/utils'
import { useSystemStatus } from '@/hooks/useSystemStatus'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'

interface SystemStatusIndicatorProps {
  compact?: boolean
  showMenu?: boolean
}

export function SystemStatusIndicator({ compact = false, showMenu = false }: SystemStatusIndicatorProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { status, message, loading, activeModel } = useSystemStatus()
  const [isOpen, setIsOpen] = useState(false)

  const { colorClass, statusText, pulseClass } = (() => {
    if (loading) {
      return {
        colorClass: 'bg-muted-foreground/60',
        statusText: t('system.status.detecting'),
        pulseClass: 'animate-status-blink'
      }
    }

    switch (status) {
      case 'running':
        return {
          colorClass: 'bg-emerald-500',
          statusText: t('system.status.running'),
          pulseClass: ''
        }
      case 'limited':
        return {
          colorClass: 'bg-amber-500',
          statusText: t('system.status.limited'),
          pulseClass: 'animate-status-blink'
        }
      case 'stopped':
        return {
          colorClass: 'bg-red-500',
          statusText: t('system.status.stopped'),
          pulseClass: ''
        }
      case 'error':
        return {
          colorClass: 'bg-red-500',
          statusText: t('system.status.error'),
          pulseClass: 'animate-status-blink'
        }
      default:
        return {
          colorClass: 'bg-muted-foreground/60',
          statusText: t('system.status.detecting'),
          pulseClass: 'animate-status-blink'
        }
    }
  })()

  const formatTimestamp = (value?: string | null) => {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
      return value
    }
    return date.toLocaleString()
  }

  const getStatusDetail = () => {
    if (loading) {
      return t('system.status.detecting')
    }
    if (status === 'running') {
      // 检查测试状态
      if (activeModel?.lastTestStatus === true && activeModel?.lastTestedAt) {
        // 已测试且通过
        const formatted = formatTimestamp(activeModel.lastTestedAt)
        if (formatted) {
          return t('system.test.lastSuccess', { time: formatted })
        }
      } else if (activeModel?.lastTestStatus === false) {
        // 测试失败
        return activeModel.lastTestError || t('system.test.unknownReason')
      } else {
        // 未测试
        return message || t('system.messages.modelNotTested')
      }
    }
    if (status === 'limited') {
      if (activeModel?.lastTestStatus === false && activeModel?.lastTestedAt) {
        const formatted = formatTimestamp(activeModel.lastTestedAt)
        const reason = activeModel.lastTestError || t('system.test.unknownReason')
        if (formatted) {
          return t('system.test.lastFailure', { time: formatted, reason })
        }
        return reason
      }
      return message || t('system.messages.modelNotTested')
    }
    return message
  }

  const detail = getStatusDetail()

  // 判断是否显示警告图标
  const showWarning =
    status === 'limited' || status === 'error' || (status === 'running' && activeModel?.lastTestStatus !== true)

  const warningColor = status === 'error' ? 'text-red-500' : 'text-amber-500'

  // Compact mode (just status indicator dot)
  if (compact) {
    const tooltipParts = [statusText]
    if (activeModel?.name) {
      tooltipParts.push(activeModel.name)
    }
    if (detail) {
      tooltipParts.push(detail)
    }
    const tooltip = tooltipParts.filter(Boolean).join(' · ')

    return (
      <div className="flex items-center justify-center" title={tooltip || undefined}>
        <span className={cn('inline-flex size-2.5 rounded-full', colorClass, pulseClass)} />
        <span className="sr-only">
          {t('system.statusLabel')}: {statusText}
        </span>
      </div>
    )
  }

  // Menu mode (with dropdown and navigation)
  if (showMenu) {
    return (
      <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground h-8 w-full justify-start gap-2 p-1.5"
            size="default">
            <div className="relative flex size-5 shrink-0 items-center justify-center">
              <span
                className={cn('inline-flex size-4 rounded-full transition-colors', colorClass, pulseClass)}
                aria-label={statusText}
              />
              {showWarning && <AlertCircle className={cn('absolute -top-1 -right-1 size-3', warningColor)} />}
            </div>
            <div className="flex min-w-0 flex-1 items-center gap-1.5 truncate group-data-[collapsible=icon]:hidden">
              <span className="truncate text-sm font-medium">{statusText}</span>
              {activeModel?.name && (
                <>
                  <span className="text-muted-foreground text-xs">·</span>
                  <span className="text-muted-foreground truncate text-xs">{activeModel.name}</span>
                </>
              )}
            </div>
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="start" side="top" className="w-64">
          {/* 状态信息 */}
          <div className="px-2 py-3">
            <div className="flex items-center gap-2">
              <span className={cn('inline-flex size-2.5 shrink-0 rounded-full', colorClass)} />
              <div className="flex-1 space-y-1">
                <div className="text-sm font-semibold">{t('system.statusLabel')}</div>
                <div className="text-sm">{statusText}</div>
                {activeModel?.name && <div className="text-muted-foreground text-xs">{activeModel.name}</div>}
                {detail && <div className="text-muted-foreground text-xs">{detail}</div>}
              </div>
            </div>
          </div>

          <DropdownMenuSeparator />

          {/* 快捷操作 */}
          <DropdownMenuItem
            onClick={() => {
              navigate('/activity')
              setIsOpen(false)
            }}>
            <Activity className="mr-2 size-4" />
            <span>{t('menu.activity')}</span>
          </DropdownMenuItem>

          <DropdownMenuItem
            onClick={() => {
              navigate('/settings')
              setIsOpen(false)
            }}>
            <Settings className="mr-2 size-4" />
            <span>{t('menu.settings')}</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
  }

  // Default mode (inline display)
  return (
    <div className="bg-background/90 text-muted-foreground border-border/80 flex items-center gap-2 rounded-full border px-3 py-2 text-xs shadow-sm backdrop-blur">
      <span className={cn('inline-flex size-2.5 shrink-0 rounded-full', colorClass, pulseClass)} />
      <div className="flex min-w-0 flex-col">
        <span className="text-foreground text-xs leading-tight font-semibold">{t('system.statusLabel')}</span>
        <span className="text-foreground text-xs leading-tight">{statusText}</span>
        {detail ? <span className="text-muted-foreground text-[11px] leading-tight">{detail}</span> : null}
      </div>
    </div>
  )
}
