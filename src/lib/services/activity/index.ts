import { TimelineDay } from '@/lib/types/activity'
import { buildEventSummaryFromRaw } from './utils'
import {
  getActivityCountByDate as apiGetActivityCountByDate,
  getActivitiesIncremental as apiGetActivitiesIncremental,
  deleteActivity as apiDeleteActivity
} from '@/lib/client/apiClient'

/**
 * Fetch daily activity totals (actual counts in the DB)
 * Different from paged data; reflects the true per-day counts in the DB
 */
export async function fetchActivityCountByDate(): Promise<Record<string, number>> {
  try {
    console.debug('[fetchActivityCountByDate] Start querying daily activity totals')

    const response = await apiGetActivityCountByDate({})

    if (
      !response ||
      !('success' in response) ||
      !response.success ||
      !('data' in response) ||
      !response.data ||
      typeof response.data !== 'object' ||
      !('dateCountMap' in response.data)
    ) {
      console.warn('[fetchActivityCountByDate] Query failed or returned no data')
      return {}
    }

    const data = response.data as {
      dateCountMap?: Record<string, number>
      totalDates?: number
      totalActivities?: number
    }

    console.debug('[fetchActivityCountByDate] ✅ Query succeeded', {
      totalDates: data.totalDates,
      totalActivities: data.totalActivities
    })

    return data.dateCountMap || {}
  } catch (error) {
    console.error('[fetchActivityCountByDate] Query failed:', error)
    return {}
  }
}

/**
 * Fetch incremental activity updates (by version)
 * Used when the window is focused to pull new activities after backend events
 * @param version Current client version
 * @param limit Maximum number of activities to return
 */
export async function fetchActivitiesIncremental(version: number, limit: number = 15): Promise<TimelineDay[]> {
  try {
    console.debug('[fetchActivitiesIncremental] Start fetching incremental updates', { version, limit })

    const response = await apiGetActivitiesIncremental({ version, limit })

    if (
      !response ||
      !('success' in response) ||
      !response.success ||
      !('data' in response) ||
      !response.data ||
      typeof response.data !== 'object' ||
      !('activities' in response.data)
    ) {
      console.warn('[fetchActivitiesIncremental] Query failed or no new activities')
      return []
    }

    const data = response.data as { activities?: any[]; count?: number; maxVersion?: number }

    if (!Array.isArray(data.activities)) {
      console.warn('[fetchActivitiesIncremental] activities is not an array')
      return []
    }

    // Build activity objects and group by date
    const activitiesByDate = new Map<string, any[]>()

    data.activities.forEach((activity: any) => {
      // Safely parse startTime (either startTime or start_time)
      const startTimeStr = activity.startTime || activity.start_time
      let startTimestamp = Date.now()
      if (startTimeStr) {
        const parsed = new Date(startTimeStr).getTime()
        if (!isNaN(parsed)) {
          startTimestamp = parsed
        }
      }

      const d = new Date(startTimestamp)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      const dateStr = `${year}-${month}-${day}`

      if (!activitiesByDate.has(dateStr)) {
        activitiesByDate.set(dateStr, [])
      }

      // Convert backend sourceEvents into frontend eventSummaries
      const rawEvents = activity.sourceEvents ?? activity.source_events ?? []
      const eventSummaries = Array.isArray(rawEvents)
        ? rawEvents.map((event: any, idx: number) => buildEventSummaryFromRaw(event, idx))
        : []

      const sourceEventIds = Array.isArray(activity.sourceEventIds ?? activity.source_event_ids)
        ? (activity.sourceEventIds ?? activity.source_event_ids).map((id: any) => String(id))
        : []

      activitiesByDate.get(dateStr)!.push({
        id: activity.id,
        title: activity.title ?? activity.description ?? 'Untitled activity',
        name: activity.title ?? activity.description ?? 'Untitled activity',
        description: activity.description,
        timestamp: startTimestamp, // Ensure timestamp is set
        startTime: startTimestamp,
        endTime: activity.endTime ? new Date(activity.endTime).getTime() : startTimestamp,
        eventSummaries: eventSummaries,
        sourceEventIds,
        version: activity.version,
        isNew: true // Flag as new for animations
      })
    })

    // Build timeline data
    const timelineData: TimelineDay[] = Array.from(activitiesByDate.entries())
      .sort(([dateA], [dateB]) => (dateA > dateB ? -1 : 1))
      .map(([date, activities]) => ({
        date,
        activities: activities.sort((a, b) => b.timestamp - a.timestamp), // Sort descending by timestamp
        isNew: true // Mark the day group as new
      }))

    console.debug('[fetchActivitiesIncremental] ✅ Fetch succeeded', {
      newActivities: data.count,
      maxVersion: data.maxVersion
    })

    return timelineData
  } catch (error) {
    console.error('[fetchActivitiesIncremental] Fetch failed:', error)
    return []
  }
}

/**
 * Delete a specific activity
 * @param activityId Activity ID
 */
export async function deleteActivity(activityId: string): Promise<boolean> {
  try {
    console.debug('[deleteActivity] Start deleting activity', activityId)

    const response = await apiDeleteActivity({ activityId })

    if (!response?.success) {
      console.warn('[deleteActivity] Delete failed', { activityId, error: response?.error })
      return false
    }

    console.debug('[deleteActivity] ✅ Delete succeeded', activityId)
    return true
  } catch (error) {
    console.error('[deleteActivity] Delete failed:', error)
    return false
  }
}
