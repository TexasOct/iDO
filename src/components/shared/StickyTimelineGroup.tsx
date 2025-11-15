/**
 * StickyTimelineGroup Component
 *
 * A reusable timeline component with sticky date headers.
 * When scrolling, each date header sticks to the top until replaced by the next one.
 * Uses CSS sticky positioning for native, smooth behavior.
 */

import { format } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'
import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface StickyTimelineGroupProps<T> {
  /** Array of items to display in timeline */
  items: T[]
  /** Function to extract date from item (returns ISO string or timestamp) */
  getDate: (item: T) => string | number | undefined
  /** Function to render each item */
  renderItem: (item: T) => ReactNode
  /** Custom empty state message */
  emptyMessage?: string
  /** Custom className for the container */
  className?: string
  /** Custom format for date display (default: 'yyyy年MM月dd日 EEEE') */
  dateFormat?: string
  /** Show item count in header */
  showCount?: boolean
  /** Custom count text (receives count as parameter) */
  countText?: (count: number) => string
  /** Optional map of date to actual total count in database (overrides local count) */
  dateCountMap?: Record<string, number>
  /** Custom className for sticky header container */
  headerClassName?: string
  /** Custom className for header title */
  headerTitleClassName?: string
  /** Custom className for header count text */
  headerCountClassName?: string
  /** Custom className for items container */
  itemsContainerClassName?: string
}

interface GroupedItems<T> {
  date: string
  formattedDate: string
  items: T[]
  count: number
}

/**
 * Groups items by date and displays them in a timeline format with sticky headers
 */
export function StickyTimelineGroup<T extends { id: string }>({
  items,
  getDate,
  renderItem,
  emptyMessage,
  className = '',
  dateFormat,
  showCount = true,
  countText,
  dateCountMap,
  headerClassName = '',
  headerTitleClassName = '',
  headerCountClassName = '',
  itemsContainerClassName = ''
}: StickyTimelineGroupProps<T>) {
  const { t, i18n } = useTranslation()

  // Auto-detect locale
  const locale = i18n.language === 'zh-CN' ? zhCN : enUS
  const defaultFormat = i18n.language === 'zh-CN' ? 'yyyy年MM月dd日 EEEE' : 'MMMM d, yyyy (EEEE)'
  const finalDateFormat = dateFormat || defaultFormat

  // Group items by date
  const groupedItems = groupItemsByDate(items, getDate, locale, finalDateFormat, dateCountMap)

  if (groupedItems.length === 0) {
    return (
      <div className={`border-muted/60 rounded-2xl border border-dashed p-10 text-center ${className}`}>
        <p className="text-muted-foreground text-sm">{emptyMessage || t('common.noData', 'No data available')}</p>
      </div>
    )
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Timeline sections - each with sticky header */}
      {groupedItems.map((group) => (
        <div key={group.date} className="relative">
          {/* Sticky Date Header - sticks to top until next one replaces it */}
          <div className={cn('bg-background sticky top-0 z-10 px-6', headerClassName)}>
            <h2 className={cn('text-lg font-semibold', headerTitleClassName)}>{group.formattedDate}</h2>
            {showCount && (
              <p className={cn('text-muted-foreground text-sm', headerCountClassName)}>
                {countText ? countText(group.count) : `${group.count} ${t('activity.activitiesCount')}`}
              </p>
            )}
          </div>

          {/* Gradient fade mask below sticky header */}
          <div className="from-background/0 to-background pointer-events-none sticky top-12 z-10 h-9 bg-linear-to-t" />

          {/* Items */}
          <div className={cn('space-y-3 px-6 pb-6', itemsContainerClassName)}>
            {group.items.map((item) => (
              <div key={item.id}>{renderItem(item)}</div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

/**
 * Helper function to group items by date
 */
function groupItemsByDate<T>(
  items: T[],
  getDate: (item: T) => string | number | undefined,
  locale: typeof zhCN | typeof enUS,
  dateFormat: string,
  dateCountMap?: Record<string, number>
): GroupedItems<T>[] {
  // Create a map to group items by date
  const groups = new Map<string, T[]>()

  items.forEach((item) => {
    const dateValue = getDate(item)
    if (!dateValue) return

    // Parse date
    const date = typeof dateValue === 'string' ? new Date(dateValue) : new Date(dateValue)

    // Format as YYYY-MM-DD for grouping
    const dateKey = format(date, 'yyyy-MM-dd')

    if (!groups.has(dateKey)) {
      groups.set(dateKey, [])
    }
    groups.get(dateKey)!.push(item)
  })

  // Convert to array and sort by date (newest first)
  const result: GroupedItems<T>[] = Array.from(groups.entries())
    .map(([dateKey, items]) => {
      const [year, month, day] = dateKey.split('-').map(Number)
      const date = new Date(year, month - 1, day)

      // Use actual count from dateCountMap if available, otherwise use loaded items count
      const actualCount = dateCountMap?.[dateKey] ?? items.length

      return {
        date: dateKey,
        formattedDate: format(date, dateFormat, { locale }),
        items,
        count: actualCount
      }
    })
    .sort((a, b) => b.date.localeCompare(a.date)) // Sort newest first

  return result
}
