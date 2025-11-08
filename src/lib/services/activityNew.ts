import { getActivities, getActivityById, getEventById, deleteActivity, deleteEvent } from '@/lib/client/apiClient'

interface ApiResponse<T> {
  success?: boolean
  message?: string
  data?: T
}

const ensureSuccess = <T>(response: ApiResponse<T>): T => {
  if (!response?.success) {
    throw new Error(response?.message ?? 'Unknown backend error')
  }
  if (!response.data) {
    throw new Error('Backend returned empty data')
  }
  return response.data
}

export interface ActivitySummary {
  id: string
  title: string
  description?: string
  startTime: string
  endTime: string
  createdAt?: string
  sourceEventIds: string[]
}

export interface ActivityEventDetail {
  id: string
  summary: string
  keywords: string[]
  timestamp: number
  screenshots: string[]
}

const parseIsoToTimestamp = (value?: string): number => {
  if (!value) return Date.now()
  const parsed = new Date(value).getTime()
  return Number.isNaN(parsed) ? Date.now() : parsed
}

const normalizeScreenshots = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return []
  }
  const normalized: string[] = []
  for (const item of value) {
    if (typeof item !== 'string') continue
    const trimmed = item.trim()
    if (!trimmed) continue
    normalized.push(trimmed)
    if (normalized.length >= 6) break
  }
  return normalized
}

const normalizeActivity = (activity: any): ActivitySummary => ({
  id: String(activity.id ?? ''),
  title: String(activity.title ?? activity.description ?? ''),
  description: activity.description ? String(activity.description) : undefined,
  startTime: String(activity.startTime ?? activity.start_time ?? ''),
  endTime: String(activity.endTime ?? activity.end_time ?? ''),
  createdAt: activity.createdAt ?? activity.created_at,
  sourceEventIds: Array.isArray(activity.sourceEventIds ?? activity.source_event_ids)
    ? (activity.sourceEventIds ?? activity.source_event_ids).map((id: any) => String(id))
    : []
})

export async function fetchActivities(limit: number, offset = 0): Promise<ActivitySummary[]> {
  const response = await getActivities({ limit, offset })
  const data = ensureSuccess<{ activities?: any[] }>(response as ApiResponse<{ activities?: any[] }>)
  const activities = Array.isArray(data.activities) ? data.activities : []
  return activities.map(normalizeActivity)
}

export async function fetchActivityById(activityId: string): Promise<ActivitySummary | null> {
  const response = await getActivityById({ activityId })
  const data = ensureSuccess<any>(response as ApiResponse<any>)
  if (!data) return null
  return normalizeActivity(data)
}

export async function fetchEventsByIds(eventIds: string[]): Promise<ActivityEventDetail[]> {
  if (!eventIds.length) return []

  const uniqueIds = Array.from(new Set(eventIds))
  const details = await Promise.all(
    uniqueIds.map(async (eventId) => {
      const response = await getEventById({ eventId })
      const data = ensureSuccess<any>(response as ApiResponse<any>)
      return {
        id: String(data.id ?? eventId),
        summary: String(data.summary ?? ''),
        keywords: Array.isArray(data.keywords) ? data.keywords.map((keyword: any) => String(keyword)) : [],
        timestamp: parseIsoToTimestamp(data.startTime ?? data.start_time ?? data.timestamp),
        screenshots: normalizeScreenshots(data.screenshots)
      }
    })
  )

  // Preserve original order from eventIds input
  const detailMap = new Map(details.map((detail) => [detail.id, detail]))
  return eventIds
    .map((id) => detailMap.get(id) ?? null)
    .filter((detail): detail is ActivityEventDetail => detail !== null)
}

export async function removeActivity(activityId: string): Promise<void> {
  console.log('[activityNew] removeActivity called with:', activityId)
  const response = await deleteActivity({ activityId })
  console.log('[activityNew] deleteActivity response:', response)
  if (!response?.success) {
    throw new Error(response?.message ?? 'Failed to delete activity')
  }
}

export async function removeEvent(eventId: string): Promise<void> {
  console.log('[activityNew] removeEvent called with:', eventId)
  const response = await deleteEvent({ eventId })
  console.log('[activityNew] deleteEvent response:', response)
  if (!response?.success) {
    throw new Error(response?.message ?? 'Failed to delete event')
  }
}
