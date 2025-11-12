/**
 * TimeDisplay Component
 *
 * A reusable component for displaying timestamps in a consistent format.
 * Shows both the exact time (HH:mm:ss) and relative time (e.g., "2 hours ago").
 *
 * @example
 * ```tsx
 * <TimeDisplay timestamp={1234567890} locale={zhCN} />
 * ```
 */

import { format, formatDistanceToNow } from 'date-fns'
import type { Locale } from 'date-fns'
import { useTranslation } from 'react-i18next'
import { enUS, zhCN } from 'date-fns/locale'

interface TimeDisplayProps {
  /** Timestamp in milliseconds or ISO date string */
  timestamp: number | string
  /** Optional date-fns locale for formatting */
  locale?: Locale
  /** Custom className for styling */
  className?: string
  /** Show date in addition to time (default: false) */
  showDate?: boolean
  /** Separator between time and relative time (default: "·") */
  separator?: string
}

/**
 * TimeDisplay component that shows both exact time and relative time
 */
export function TimeDisplay({
  timestamp,
  locale,
  className = 'text-muted-foreground text-xs',
  showDate = false,
  separator = '·'
}: TimeDisplayProps) {
  const { i18n } = useTranslation()

  // Auto-detect locale if not provided
  const effectiveLocale = locale || (i18n.language === 'zh-CN' ? zhCN : enUS)

  // Parse timestamp
  const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp)

  // Format exact time
  const timeFormat = showDate ? 'yyyy-MM-dd HH:mm:ss' : 'HH:mm:ss'
  const exactTime = format(date, timeFormat)

  // Format relative time
  const relativeTime = formatDistanceToNow(date, {
    addSuffix: true,
    locale: effectiveLocale
  })

  return (
    <span className={className}>
      <span>{exactTime}</span>
      <span className="mx-1.5">{separator}</span>
      <span>{relativeTime}</span>
    </span>
  )
}

/**
 * Compact version that only shows relative time
 */
export function TimeDisplayCompact({
  timestamp,
  locale,
  className = 'text-muted-foreground text-xs'
}: Omit<TimeDisplayProps, 'showDate' | 'separator'>) {
  const { i18n } = useTranslation()

  // Auto-detect locale if not provided
  const effectiveLocale = locale || (i18n.language === 'zh-CN' ? zhCN : enUS)

  // Parse timestamp
  const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp)

  // Format relative time
  const relativeTime = formatDistanceToNow(date, {
    addSuffix: true,
    locale: effectiveLocale
  })

  return <span className={className}>{relativeTime}</span>
}

/**
 * Detailed version that shows date, time, and relative time
 */
export function TimeDisplayDetailed({
  timestamp,
  locale,
  className = 'text-muted-foreground text-xs'
}: Omit<TimeDisplayProps, 'showDate' | 'separator'>) {
  return <TimeDisplay timestamp={timestamp} locale={locale} className={className} showDate={true} />
}
