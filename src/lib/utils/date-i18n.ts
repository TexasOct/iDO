import { format, type Locale } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'

/**
 * Date formatting and i18n utilities
 */

/**
 * Get date-fns locale based on i18n language
 */
export function getDateLocale(language: string): Locale {
  return language.startsWith('zh') ? zhCN : enUS
}

/**
 * Date format types
 */
export type DateFormatType = 'full' | 'month' | 'year' | 'weekday'

/**
 * Get date format string based on language and type
 */
export function getDateFormat(language: string, type: DateFormatType = 'full'): string {
  const isZh = language.startsWith('zh')

  switch (type) {
    case 'full':
      return isZh ? 'yyyy年MM月dd日 EEEE' : 'PPP, EEEE'
    case 'month':
      return isZh ? 'yyyy年MM月' : 'MMMM yyyy'
    case 'year':
      return isZh ? 'yyyy年' : 'yyyy'
    case 'weekday':
      return 'EEE'
    default:
      return isZh ? 'yyyy年MM月dd日' : 'PPP'
  }
}

/**
 * Format a Date object to YYYY-MM-DD string
 */
export function formatDateString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Parse YYYY-MM-DD string to Date object, avoiding timezone issues
 * by manually splitting and constructing the date
 */
export function parseDateString(dateStr: string): Date {
  const [year, month, day] = dateStr.split('-').map(Number)
  return new Date(year, month - 1, day)
}

/**
 * Format hour number to HH:00 string
 */
export function formatTime(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`
}

/**
 * Check if a date is today
 */
export function isToday(date: Date): boolean {
  const today = new Date()
  return (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  )
}

/**
 * Check if a date is in the specified month
 */
export function isInMonth(date: Date, referenceDate: Date): boolean {
  return date.getMonth() === referenceDate.getMonth() && date.getFullYear() === referenceDate.getFullYear()
}

/**
 * Format a date with i18n support
 * Convenience wrapper around date-fns format with locale
 */
export function formatDate(date: Date, language: string, formatType: DateFormatType = 'full'): string {
  const locale = getDateLocale(language)
  const formatString = getDateFormat(language, formatType)
  return format(date, formatString, { locale })
}

/**
 * Parse time string (HH:MM) to minutes since midnight
 */
export function timeToMinutes(timeStr: string): number {
  const [hours, minutes] = timeStr.split(':').map((n) => parseInt(n, 10))
  return hours * 60 + (minutes || 0)
}

/**
 * Convert minutes since midnight to HH:MM string
 */
export function minutesToTime(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`
}
