import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { Settings, Activity, AlertCircle, ChevronRight, ChevronLeft } from 'lucide-react'

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

export function FloatingStatusBall() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { status, message, loading, activeModel } = useSystemStatus()
  const [isOpen, setIsOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isNearby, setIsNearby] = useState(false)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const { colorClass, statusText, pulseClass } = (() => {
    if (loading) {
      return {
        colorClass: 'bg-muted-foreground/60',
        statusText: t('system.status.detecting'),
        pulseClass: 'animate-pulse'
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
          pulseClass: 'animate-pulse'
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
          pulseClass: 'animate-pulse'
        }
      default:
        return {
          colorClass: 'bg-muted-foreground/60',
          statusText: t('system.status.detecting'),
          pulseClass: 'animate-pulse'
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

  // 监听鼠标移动，检测是否在悬浮球附近
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return

      const rect = containerRef.current.getBoundingClientRect()
      const distance = 150 // 150px范围内显示箭头

      // 计算鼠标到悬浮球区域的距离
      const isNear =
        e.clientX >= rect.left - distance &&
        e.clientX <= rect.right + distance &&
        e.clientY >= rect.top - distance &&
        e.clientY <= rect.bottom + distance

      setIsNearby(isNear)
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  // 处理折叠/展开，添加过渡状态
  const handleToggleCollapse = () => {
    if (isTransitioning) return

    setIsTransitioning(true)
    setIsCollapsed(!isCollapsed)

    // 300ms后解除过渡状态（与CSS动画时间一致）
    setTimeout(() => {
      setIsTransitioning(false)
    }, 300)
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        'pointer-events-none fixed bottom-20 z-50 flex items-center gap-2 transition-all duration-300',
        isCollapsed ? 'right-[-40px]' : 'right-6'
      )}>
      {/* 状态球容器 */}
      <div className="pointer-events-auto flex items-center gap-2">
        {/* 收缩/展开按钮 - 只在鼠标接近时显示 */}
        {isNearby && (
          <Button
            variant="ghost"
            size="icon"
            disabled={isTransitioning}
            className={cn(
              'bg-background h-14 w-5 rounded-l-md border-y border-l shadow-md transition-all duration-300 hover:w-7',
              isTransitioning && 'cursor-not-allowed'
            )}
            onClick={handleToggleCollapse}>
            {isCollapsed ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </Button>
        )}

        {/* 状态球 */}
        <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className={cn(
                'bg-background h-14 w-14 rounded-full border-2 shadow-lg transition-all duration-200 hover:scale-110 hover:shadow-xl',
                isOpen && 'scale-110 shadow-xl'
              )}>
              <div className="relative flex h-full w-full items-center justify-center">
                <span
                  className={cn('inline-flex h-4 w-4 rounded-full transition-colors', colorClass, pulseClass)}
                  aria-label={statusText}
                />
                {showWarning && <AlertCircle className={cn('absolute -top-1 -right-1 h-5 w-5', warningColor)} />}
              </div>
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" side="top" className="w-64">
            {/* 状态信息 */}
            <div className="px-2 py-3">
              <div className="flex items-center gap-2">
                <span className={cn('inline-flex h-2.5 w-2.5 flex-shrink-0 rounded-full', colorClass)} />
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
              <Activity className="mr-2 h-4 w-4" />
              <span>{t('menu.activity')}</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => {
                navigate('/settings')
                setIsOpen(false)
              }}>
              <Settings className="mr-2 h-4 w-4" />
              <span>{t('menu.settings')}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
