import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format duration in milliseconds to human-readable string
 * @param durationMs Duration in milliseconds
 * @param format 'short' (5m 30s) or 'long' (5 minutes 30 seconds)
 * @returns Formatted duration string
 */
export function formatDuration(durationMs: number, format: 'short' | 'long' = 'short'): string {
  const totalSeconds = Math.floor(durationMs / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (format === 'short') {
    const parts: string[] = []
    if (hours > 0) parts.push(`${hours}h`)
    if (minutes > 0) parts.push(`${minutes}m`)
    if (seconds > 0 || parts.length === 0) parts.push(`${seconds}s`)
    return parts.join(' ')
  } else {
    const parts: string[] = []
    if (hours > 0) parts.push(`${hours} ${hours === 1 ? 'hour' : 'hours'}`)
    if (minutes > 0) parts.push(`${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`)
    if (seconds > 0 || parts.length === 0) parts.push(`${seconds} ${seconds === 1 ? 'second' : 'seconds'}`)
    return parts.join(' ')
  }
}
