/**
 * Three-Layer Architecture Data Service
 *
 * Reads from the new three-layer database schema:
 * - actions (fine-grained operations)
 * - events_v2 (medium-grained work segments)
 * - activities_v2 (coarse-grained work sessions)
 */

import Database from '@tauri-apps/plugin-sql'
import { Activity, Event, Action, TimelineDay } from '@/lib/types/activity'
import { getDatabasePath } from '@/lib/client/apiClient'

export interface TimelineQuery {
  start?: string
  end?: string
  limit?: number
  offset?: number
}

let dbInstance: Promise<Database> | null = null

async function resolvePathFromBackend(): Promise<string | null> {
  try {
    const response = await getDatabasePath()

    if (
      response &&
      'success' in response &&
      response.success &&
      'data' in response &&
      response.data &&
      typeof response.data === 'object' &&
      'path' in response.data &&
      typeof response.data.path === 'string'
    ) {
      return response.data.path
    }
  } catch (error) {
    console.warn('[three-layer-db] Failed to fetch database path from backend', error)
  }
  return null
}

async function resolveDatabase(): Promise<Database> {
  if (!dbInstance) {
    dbInstance = (async () => {
      const backendPath = await resolvePathFromBackend()

      if (!backendPath) {
        throw new Error('Failed to get database path from backend')
      }

      const connection = backendPath.startsWith('sqlite:') ? backendPath : `sqlite:${backendPath}`

      try {
        console.debug('[three-layer-db] Connecting to database:', connection)
        const db = await Database.load(connection)

        // Verify activities_v2 table exists
        const hasActivitiesV2 = await db
          .select<
            { name: string }[]
          >("SELECT name FROM sqlite_master WHERE type = 'table' AND name = $1", ['activities_v2'])
          .catch(() => [])

        if (hasActivitiesV2.length === 0) {
          console.warn('[three-layer-db] activities_v2 table not found, database may not be migrated yet')
        }

        return db
      } catch (error) {
        console.error('[three-layer-db] Failed to connect to database:', error)
        throw error
      }
    })()
  }

  return dbInstance
}

interface ActivityV2Row {
  id: string
  title: string
  description: string
  start_time: string
  end_time: string
  source_event_ids: string | null
  session_duration_minutes: number | null
  topic_tags: string | null
  user_merged_from_ids: string | null
  user_split_into_ids: string | null
  created_at: string
  updated_at: string
}

interface EventV2Row {
  id: string
  title: string
  description: string
  start_time: string
  end_time: string
  source_action_ids: string | null
  created_at: string
}

interface ActionRow {
  id: string
  title: string
  description: string
  keywords: string | null
  timestamp: string
  created_at: string
}

const parseDate = (dateStr: string | undefined | null): number => {
  if (!dateStr) {
    console.warn(`[three-layer-db] Invalid date string: "${dateStr}", using current time`)
    return Date.now()
  }
  const parsed = new Date(dateStr).getTime()
  if (isNaN(parsed)) {
    console.warn(`[three-layer-db] Failed to parse date: "${dateStr}", using current time`)
    return Date.now()
  }
  return parsed
}

const parseJsonArray = <T = string>(value: string | null): T[] => {
  if (!value) return []
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch (error) {
    console.warn('[three-layer-db] Failed to parse JSON array:', error)
    return []
  }
}

function mapActivityV2Row(row: ActivityV2Row): Activity {
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    startTime: parseDate(row.start_time),
    endTime: parseDate(row.end_time),
    sourceEventIds: parseJsonArray(row.source_event_ids),
    sessionDurationMinutes: row.session_duration_minutes ?? undefined,
    topicTags: parseJsonArray(row.topic_tags),
    userMergedFromIds: parseJsonArray(row.user_merged_from_ids),
    userSplitIntoIds: parseJsonArray(row.user_split_into_ids),
    createdAt: parseDate(row.created_at),
    updatedAt: parseDate(row.updated_at)
  }
}

function mapEventV2Row(row: EventV2Row): Event {
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    startTime: parseDate(row.start_time),
    endTime: parseDate(row.end_time),
    sourceActionIds: parseJsonArray(row.source_action_ids),
    createdAt: parseDate(row.created_at)
  }
}

// Note: Action screenshots are loaded via backend API handler (get_actions_by_event)
// This ensures consistent data access patterns and avoids direct database queries from frontend
function mapActionRow(row: ActionRow): Action {
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    keywords: parseJsonArray(row.keywords),
    timestamp: parseDate(row.timestamp),
    screenshots: [], // Screenshots are loaded via backend API
    createdAt: parseDate(row.created_at)
  }
}

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
 * Fetch activities (work sessions) for timeline display
 */
export async function fetchActivityTimeline(query: TimelineQuery): Promise<TimelineDay[]> {
  const { start, end, limit = 50, offset = 0 } = query
  const db = await resolveDatabase()

  let parameterIndex = 1
  const filters: string[] = ['deleted = 0']
  const bindValues: (string | number)[] = []

  if (start) {
    filters.push(`date(start_time) >= date($${parameterIndex})`)
    bindValues.push(start)
    parameterIndex += 1
  }

  if (end) {
    filters.push(`date(start_time) <= date($${parameterIndex})`)
    bindValues.push(end)
    parameterIndex += 1
  }

  let sql = `
    SELECT
      id, title, description, start_time, end_time,
      source_event_ids, session_duration_minutes, topic_tags,
      user_merged_from_ids, user_split_into_ids,
      created_at, updated_at
    FROM activities_v2
    WHERE ${filters.join(' AND ')}
    ORDER BY start_time DESC
    LIMIT $${parameterIndex}
  `
  bindValues.push(limit)
  parameterIndex += 1

  if (offset > 0) {
    sql += ` OFFSET $${parameterIndex}`
    bindValues.push(offset)
  }

  console.debug('[three-layer-db] Fetching activities, SQL:', sql)
  const rows = await db.select<ActivityV2Row[]>(sql, bindValues)
  const activities = rows.map(mapActivityV2Row)

  return buildTimeline(activities)
}

/**
 * Fetch a single activity by ID
 */
export async function fetchActivityDetails(activityId: string): Promise<Activity | null> {
  const db = await resolveDatabase()

  const rows = await db.select<ActivityV2Row[]>(
    `
    SELECT
      id, title, description, start_time, end_time,
      source_event_ids, session_duration_minutes, topic_tags,
      user_merged_from_ids, user_split_into_ids,
      created_at, updated_at
    FROM activities_v2
    WHERE id = ? AND deleted = 0
    `,
    [activityId]
  )

  if (rows.length === 0) {
    console.warn('[three-layer-db] Activity not found:', activityId)
    return null
  }

  return mapActivityV2Row(rows[0])
}

/**
 * Fetch events (work segments) for an activity - DRILL-DOWN
 */
export async function fetchEventsByActivity(activityId: string): Promise<Event[]> {
  const db = await resolveDatabase()

  // First get the activity to find source event IDs
  const activity = await fetchActivityDetails(activityId)
  if (!activity || !activity.sourceEventIds.length) {
    console.warn('[three-layer-db] Activity has no source events:', activityId)
    return []
  }

  // Build SQL for fetching multiple events
  const placeholders = activity.sourceEventIds.map(() => '?').join(',')
  const sql = `
    SELECT
      id, title, description, start_time, end_time,
      source_action_ids, created_at
    FROM events_v2
    WHERE id IN (${placeholders}) AND deleted = 0
    ORDER BY start_time DESC
  `

  const rows = await db.select<EventV2Row[]>(sql, activity.sourceEventIds)
  return rows.map(mapEventV2Row)
}

/**
 * Fetch actions (fine-grained operations) for an event - DRILL-DOWN
 */
export async function fetchActionsByEvent(eventId: string): Promise<Action[]> {
  const db = await resolveDatabase()

  // First get the event to find source action IDs
  const rows = await db.select<EventV2Row[]>(
    `
    SELECT id, title, description, start_time, end_time,
           source_action_ids, created_at
    FROM events_v2
    WHERE id = ? AND deleted = 0
    `,
    [eventId]
  )

  if (rows.length === 0) {
    console.warn('[three-layer-db] Event not found:', eventId)
    return []
  }

  const event = mapEventV2Row(rows[0])
  if (!event.sourceActionIds.length) {
    console.warn('[three-layer-db] Event has no source actions:', eventId)
    return []
  }

  // Build SQL for fetching multiple actions
  const placeholders = event.sourceActionIds.map(() => '?').join(',')
  const sql = `
    SELECT
      id, title, description, keywords, timestamp, created_at
    FROM actions
    WHERE id IN (${placeholders}) AND deleted = 0
    ORDER BY timestamp DESC
  `

  const actionRows = await db.select<ActionRow[]>(sql, event.sourceActionIds)
  return actionRows.map(mapActionRow)
}

/**
 * Get activity count grouped by date
 */
export async function fetchActivityCountByDate(): Promise<Record<string, number>> {
  const db = await resolveDatabase()

  const rows = await db.select<{ date: string; count: number }[]>(
    `
    SELECT DATE(start_time) as date, COUNT(*) as count
    FROM activities_v2
    WHERE deleted = 0
    GROUP BY DATE(start_time)
    ORDER BY date DESC
    `
  )

  const result: Record<string, number> = {}
  rows.forEach((row) => {
    result[row.date] = row.count
  })

  return result
}
