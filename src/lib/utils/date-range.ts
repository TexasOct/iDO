import { addDays, endOfDay, endOfMonth, format, startOfDay, startOfMonth, subDays } from 'date-fns'

import { TrendDimension, TrendRange } from '@/lib/types/dashboard'

export const formatAsLocalISO = (date: Date) => format(date, "yyyy-MM-dd'T'HH:mm:ss")

export const createDayRange = (date: Date): TrendRange => {
  const start = startOfDay(date)
  const end = endOfDay(date)
  return {
    startDate: formatAsLocalISO(start),
    endDate: formatAsLocalISO(end)
  }
}

export const createWeekRange = (startDate: Date): TrendRange => {
  const start = startOfDay(startDate)
  const end = endOfDay(addDays(start, 6))
  return {
    startDate: formatAsLocalISO(start),
    endDate: formatAsLocalISO(end)
  }
}

export const createMonthRange = (year: number, monthIndex: number): TrendRange => {
  const start = startOfMonth(new Date(year, monthIndex, 1))
  const end = endOfDay(endOfMonth(start))
  return {
    startDate: formatAsLocalISO(start),
    endDate: formatAsLocalISO(end)
  }
}

export const createCustomRange = (start: Date, end: Date): TrendRange => {
  const orderedStart = start < end ? start : end
  const orderedEnd = end >= start ? end : start
  return {
    startDate: formatAsLocalISO(startOfDay(orderedStart)),
    endDate: formatAsLocalISO(endOfDay(orderedEnd))
  }
}

export const getDefaultRangeForDimension = (dimension: TrendDimension): TrendRange => {
  const today = new Date()

  switch (dimension) {
    case 'day':
      return createDayRange(today)
    case 'week':
      return createWeekRange(subDays(today, 6))
    case 'month': {
      const base = startOfMonth(today)
      return createMonthRange(base.getFullYear(), base.getMonth())
    }
    case 'custom':
    default:
      return createCustomRange(subDays(today, 29), today)
  }
}
