/**
 * Activity API Service Layer
 *
 * This module provides a clean API-based interface for activity data access,
 * replacing direct SQL database queries with backend API calls.
 *
 * Migration from SQL-based services:
 * - Old: src/lib/services/activity/db.ts (direct SQL queries)
 * - Old: src/lib/services/activity/three-layer-db.ts (direct SQL queries)
 * - New: This file uses apiClient for all data access
 */

import { TimelineDay, Activity, Event, Action } from '@/lib/types/activity'
import {
  getActivities,
  getActivityById,
  getActivityCountByDate,
  getEventsByActivity,
  getActionsByEvent
} from '@/lib/client/apiClient'

export interface TimelineQuery {
  start?: string
  end?: string
  limit?: number
  offset?: number
}

/**
 * Build timeline grouped by date from activities array
 */
function buildTimeline(activities: Activity[]): TimelineDay[] {
  const grouped = new Map<string, Activity[]>()

  activities.forEach((activity) => {
    if (typeof activity.startTime !== 'number' || isNaN(activity.startTime)) {
      console.warn(`[buildTimeline] Invalid activity startTime: ${activity.startTime}`, activity.id)
      return
    }

    const d = new Date(activity.startTime)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const date = `${year}-${month}-${day}`

    if (!grouped.has(date)) {
      grouped.set(date, [])
    }
    grouped.get(date)!.push(activity)
  })

  const sortedDates = Array.from(grouped.keys()).sort((a, b) => (a > b ? -1 : 1))

  return sortedDates.map((date) => {
    const dayActivities = grouped.get(date) ?? []
    dayActivities.sort((a, b) => b.startTime - a.startTime)
    return {
      date,
      activities: dayActivities
    }
  })
}

/**
 * Fetch activities timeline using backend API
 *
 * Replaces SQL-based fetchActivityTimeline from db.ts and three-layer-db.ts
 */
export async function fetchActivityTimeline(query: TimelineQuery): Promise<TimelineDay[]> {
  const { start, end, limit = 50, offset = 0 } = query

  try {
    console.debug('[api] Fetching activity timeline via API:', { start, end, limit, offset })

    const response = await getActivities({
      limit,
      offset,
      start: start || undefined,
      end: end || undefined
    })

    if (!response.success || !response.data) {
      console.error('[api] Failed to fetch activities:', response.error)
      return []
    }

    // Extract activities array from response data
    const activitiesData = (response.data as any).activities || []

    // Map API response to Activity[] type
    const activities: Activity[] = activitiesData.map((item: any) => ({
      id: item.id,
      title: item.title,
      description: item.description,
      startTime: new Date(item.startTime).getTime(),
      endTime: new Date(item.endTime).getTime(),
      sourceEventIds: item.sourceEventIds || [],
      sessionDurationMinutes: undefined,
      topicTags: [],
      createdAt: new Date(item.createdAt).getTime(),
      updatedAt: new Date(item.createdAt).getTime()
    }))

    return buildTimeline(activities)
  } catch (error) {
    console.error('[api] Error fetching activity timeline:', error)
    return []
  }
}

/**
 * Fetch single activity details using backend API
 *
 * Replaces SQL-based fetchActivityDetails from db.ts and three-layer-db.ts
 */
export async function fetchActivityDetails(activityId: string): Promise<Activity | null> {
  try {
    console.debug('[api] Fetching activity details via API:', activityId)

    const response = await getActivityById({ activityId })

    if (!response.success || !response.data) {
      console.warn('[api] Activity not found:', activityId)
      return null
    }

    const data = response.data as any

    return {
      id: data.id,
      title: data.title,
      description: data.description,
      startTime: new Date(data.startTime).getTime(),
      endTime: new Date(data.endTime).getTime(),
      sourceEventIds: data.sourceEventIds || [],
      sessionDurationMinutes: undefined,
      topicTags: [],
      createdAt: new Date(data.createdAt).getTime(),
      updatedAt: new Date(data.createdAt).getTime()
    }
  } catch (error) {
    console.error('[api] Error fetching activity details:', error)
    return null
  }
}

/**
 * Fetch events for an activity (drill-down) using backend API
 *
 * Replaces SQL-based fetchEventsByActivity from three-layer-db.ts
 */
export async function fetchEventsByActivityId(activityId: string): Promise<Event[]> {
  try {
    console.debug('[api] Fetching events for activity via API:', activityId)

    const response = await getEventsByActivity({
      activityId
    })

    if (!response.success || !response.events) {
      console.warn('[api] No events found for activity:', activityId)
      return []
    }

    return response.events.map((event: any) => ({
      id: event.id,
      title: event.title,
      description: event.description,
      startTime: new Date(event.startTime).getTime(),
      endTime: new Date(event.endTime).getTime(),
      sourceActionIds: event.sourceActionIds || [],
      createdAt: new Date(event.createdAt).getTime()
    }))
  } catch (error) {
    console.error('[api] Error fetching events for activity:', error)
    return []
  }
}

/**
 * Fetch actions for an event (drill-down) using backend API
 *
 * Replaces SQL-based fetchActionsByEvent from three-layer-db.ts
 */
export async function fetchActionsByEventId(eventId: string): Promise<Action[]> {
  try {
    console.debug('[api] Fetching actions for event via API:', eventId)

    const response = await getActionsByEvent({
      eventId
    })

    if (!response.success || !response.actions) {
      console.warn('[api] No actions found for event:', eventId)
      return []
    }

    return response.actions.map((action: any) => ({
      id: action.id,
      title: action.title,
      description: action.description,
      keywords: action.keywords || [],
      timestamp: new Date(action.timestamp).getTime(),
      screenshots: action.screenshots || [],
      createdAt: new Date(action.createdAt).getTime()
    }))
  } catch (error) {
    console.error('[api] Error fetching actions for event:', error)
    return []
  }
}

/**
 * Fetch activity count grouped by date using backend API
 *
 * Replaces SQL-based fetchActivityCountByDate from three-layer-db.ts
 */
export async function fetchActivityCountByDate(): Promise<Record<string, number>> {
  try {
    console.debug('[api] Fetching activity count by date via API')

    const response = await getActivityCountByDate({})

    if (!response.success || !response.data) {
      console.warn('[api] Failed to fetch activity count by date')
      return {}
    }

    return response.data.dateCountMap || {}
  } catch (error) {
    console.error('[api] Error fetching activity count by date:', error)
    return {}
  }
}
