/**
 * TimelineGroup Component
 *
 * A reusable timeline component that groups items by date.
 * Displays items in a chronological order with date headers.
 */

import { format } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'
import { ReactNode } from 'react'

interface TimelineGroupProps<T> {
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
}

interface GroupedItems<T> {
  date: string
  formattedDate: string
  items: T[]
  count: number
}

/**
 * Groups items by date and displays them in a timeline format
 */
export function TimelineGroup<T extends { id: string }>({
  items,
  getDate,
  renderItem,
  emptyMessage,
  className = ''
}: TimelineGroupProps<T>) {
  const { t, i18n } = useTranslation()

  // Auto-detect locale
  const locale = i18n.language === 'zh-CN' ? zhCN : enUS

  // Group items by date
  const groupedItems = groupItemsByDate(items, getDate, locale)

  if (groupedItems.length === 0) {
    return (
      <div className={`border-muted/60 rounded-2xl border border-dashed p-10 text-center ${className}`}>
        <p className="text-muted-foreground text-sm">{emptyMessage || t('common.noData', 'No data available')}</p>
      </div>
    )
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {groupedItems.map((group) => (
        <div key={group.date} className="space-y-4">
          {/* Date Header */}
          <div className="bg-background/95 supports-backdrop-filter:bg-background/60 sticky top-0 z-10 border-b pb-2 backdrop-blur">
            <h2 className="text-lg font-semibold">{group.formattedDate}</h2>
            <p className="text-muted-foreground text-sm">
              {group.count} {t('common.items', { count: group.count } as any)}
            </p>
          </div>

          {/* Items */}
          <div className="space-y-3 pl-4">
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
  locale: typeof zhCN | typeof enUS
): GroupedItems<T>[] {
  // Create a map to group items by date
  const groups = new Map<string, T[]>()

  items.forEach((item) => {
    const dateValue = getDate(item)
    if (!dateValue) return

    // Parse date
    const date = typeof dateValue === 'string' ? new Date(dateValue) : new Date(dateValue)

    // Format as YYYY-MM-DD
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

      return {
        date: dateKey,
        formattedDate: format(date, 'yyyy年MM月dd日 EEEE', { locale }),
        items,
        count: items.length
      }
    })
    .sort((a, b) => b.date.localeCompare(a.date)) // Sort newest first

  return result
}

/**
 * Compact version without sticky headers
 */
export function TimelineGroupCompact<T extends { id: string }>({
  items,
  getDate,
  renderItem,
  emptyMessage,
  className = ''
}: TimelineGroupProps<T>) {
  const { t, i18n } = useTranslation()

  const locale = i18n.language === 'zh-CN' ? zhCN : enUS
  const groupedItems = groupItemsByDate(items, getDate, locale)

  if (groupedItems.length === 0) {
    return (
      <div className={`text-muted-foreground text-center text-sm ${className}`}>
        {emptyMessage || t('common.noData', 'No data available')}
      </div>
    )
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {groupedItems.map((group) => (
        <div key={group.date} className="space-y-3">
          <h3 className="text-muted-foreground text-sm font-medium">
            {group.formattedDate} · {group.count}
          </h3>
          <div className="space-y-2">{group.items.map((item) => renderItem(item))}</div>
        </div>
      ))}
    </div>
  )
}
