import Database from '@tauri-apps/plugin-sql'
import { appDataDir, appConfigDir, resourceDir, join } from '@tauri-apps/api/path'
import { TimelineDay, Activity, EventSummary, RawRecord, LegacyEvent } from '@/lib/types/activity'
import { getDatabasePath } from '@/lib/client/apiClient'

interface ActivityRow {
  id: string
  title: string
  description: string
  start_time: string
  end_time: string
  source_events: string | ActivityRowEvent[]
  source_event_ids?: string | null
}

interface ActivityRowEvent {
  id?: string
  start_time: string
  end_time: string
  type: string
  summary?: string
  source_data?: ActivityRowRecord[]
}

interface ActivityRowRecord {
  timestamp: string
  type: string
  data?: Record<string, unknown>
  screenshot_path?: string | null
}

export interface TimelineQuery {
  start?: string
  end?: string
  limit?: number
  offset?: number
}

let dbInstance: Promise<Database> | null = null

async function tryLoadDatabase(connection: string): Promise<Database | null> {
  try {
    console.debug('[activity-db] Attempting to connect to the database', connection)
    const db = await Database.load(connection)
    const hasActivitiesTable = await db
      .select<{ name: string }[]>("SELECT name FROM sqlite_master WHERE type = 'table' AND name = $1", ['activities'])
      .catch(() => [])
    if (hasActivitiesTable.length > 0) {
      console.debug('[activity-db] Using database connection', connection)
      return db
    }
    await db.close().catch(() => false)
    console.debug('[activity-db] Missing activities table, closing connection', connection)
    return null
  } catch (error) {
    console.warn('Failed to connect to database', connection, error)
    return null
  }
}

async function buildCandidateConnections(): Promise<string[]> {
  const candidates: string[] = []

  const safePush = (value?: string | null) => {
    if (value) {
      if (value.startsWith('sqlite:')) {
        candidates.push(value)
        candidates.push(`${value}?mode=ro`)
      } else {
        candidates.push(`sqlite:${value}`)
        candidates.push(`sqlite:${value}?mode=ro`)
      }
    }
  }

  // Priority 1: read the configured path from backend config.toml
  console.debug('[activity-db] Preferring backend-provided database path')
  const backendPath = await resolvePathFromBackend()
  if (backendPath) {
    console.debug('[activity-db] Backend returned database path:', backendPath)
    safePush(backendPath)
  }

  // Priority 2: standard platform directories
  try {
    const configDir = await appConfigDir()
    const configPath = await join(configDir, 'ido.db')
    console.debug('[activity-db] Standard config directory path:', configPath)
    safePush(configPath)
  } catch (error) {
    console.warn('Failed to resolve appConfigDir', error)
  }

  try {
    const dataDir = await appDataDir()
    const dataPath = await join(dataDir, 'ido.db')
    console.debug('[activity-db] Standard data directory path:', dataPath)
    safePush(dataPath)
  } catch (error) {
    console.warn('Failed to resolve appDataDir', error)
  }

  // Priority 3: dev relative paths (last resort)
  candidates.push('sqlite:ido.db', 'sqlite:../ido.db', 'sqlite:../../ido.db')

  // Priority 4: resourceDir fallbacks (dev/build only)
  try {
    const resDir = await resourceDir()
    safePush(await join(resDir, '..', 'ido.db'))
    safePush(await join(resDir, '..', '..', 'ido.db'))
    safePush(await join(resDir, '..', '..', 'src-tauri', 'ido.db'))
    safePush(await join(resDir, '..', '..', '..', 'ido.db'))
    safePush(await join(resDir, '..', '..', '..', 'src-tauri', 'ido.db'))
    safePush(await join(resDir, '..', '..', '..', '..', 'ido.db'))
    safePush(await join(resDir, '..', '..', '..', '..', 'src-tauri', 'ido.db'))
  } catch (error) {
    console.warn('Failed to resolve resourceDir', error)
  }

  console.debug('[activity-db] Database candidate order:', candidates.slice(0, 3), '...')
  return candidates
}

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
    console.warn('Failed to fetch database path from backend', error)
  }
  return null
}

async function resolveDatabase(): Promise<Database> {
  if (!dbInstance) {
    dbInstance = (async () => {
      const candidates = await buildCandidateConnections()
      for (const candidate of candidates) {
        const db = await tryLoadDatabase(candidate)
        if (db) {
          return db
        }
      }

      throw new Error('No usable activity database found. Ensure the backend has generated data.')
    })()
  }

  return dbInstance
}

function mapRecord(eventId: string, record: ActivityRowRecord, index: number): RawRecord {
  // Safely parse record timestamp with fallback
  let timestamp: number
  if (!record.timestamp) {
    console.warn(`[mapRecord] Invalid record timestamp: "${record.timestamp}", using current time`)
    timestamp = Date.now()
  } else {
    const parsed = new Date(record.timestamp).getTime()
    timestamp = isNaN(parsed) ? Date.now() : parsed
    if (isNaN(parsed)) {
      console.warn(`[mapRecord] Failed to parse record timestamp: "${record.timestamp}", using current time`)
    }
  }

  const content = deriveRecordContent(record)
  const metadata = deriveRecordMetadata(record)

  return {
    id: `${eventId}-record-${index}`,
    timestamp,
    type: record.type,
    content,
    metadata
  }
}

function deriveRecordContent(record: ActivityRowRecord): string {
  const data = record.data ?? {}
  const type = record.type

  if (type === 'keyboard_record') {
    const text = typeof data.text === 'string' ? data.text.trim() : ''
    if (text) {
      return text
    }
    if (typeof data.key === 'string') {
      return `Key: ${data.key}`
    }
    if (typeof data.action === 'string') {
      return `Keyboard action: ${data.action}`
    }
    return 'Keyboard input'
  }

  if (type === 'mouse_record') {
    const action = typeof data.action === 'string' ? data.action : 'Mouse action'
    const button = typeof data.button === 'string' ? `(${data.button})` : ''
    return `${action}${button}`
  }

  if (type === 'screenshot_record') {
    return 'Screenshot capture'
  }

  if (typeof data.summary === 'string') {
    return data.summary
  }
  if (typeof data.title === 'string') {
    return data.title
  }

  return `${type} event`
}

function deriveRecordMetadata(record: ActivityRowRecord): Record<string, unknown> | undefined {
  const data = record.data ?? {}
  const sanitized: Record<string, unknown> = {}

  for (const [key, value] of Object.entries(data)) {
    if (key === 'img_data' || key === 'text') {
      continue
    }
    sanitized[key] = value
  }

  if (record.screenshot_path) {
    sanitized.screenshotPath = record.screenshot_path
  }

  return Object.keys(sanitized).length > 0 ? sanitized : undefined
}

function mapEvent(event: ActivityRowEvent, eventIndex: number): EventSummary {
  const eventId = event.id ?? `event-${eventIndex}`

  // Safely parse event timestamps with fallback
  let startTime: number
  let endTime: number
  let timestamp: number

  if (!event.start_time) {
    console.warn(`[mapEvent] Invalid event start_time: "${event.start_time}", using current time`)
    startTime = Date.now()
    timestamp = startTime
  } else {
    const parsed = new Date(event.start_time).getTime()
    startTime = isNaN(parsed) ? Date.now() : parsed
    timestamp = startTime
    if (isNaN(parsed)) {
      console.warn(`[mapEvent] Failed to parse event start_time: "${event.start_time}", using current time`)
    }
  }

  if (!event.end_time) {
    console.warn(`[mapEvent] Invalid event end_time: "${event.end_time}", using start_time`)
    endTime = startTime
  } else {
    const parsed = new Date(event.end_time).getTime()
    endTime = isNaN(parsed) ? startTime : parsed
    if (isNaN(parsed)) {
      console.warn(`[mapEvent] Failed to parse event end_time: "${event.end_time}", using start_time`)
    }
  }

  const records = (event.source_data ?? []).map((record, index) => mapRecord(eventId, record, index))

  const eventItem: LegacyEvent = {
    id: eventId,
    startTime,
    endTime,
    timestamp,
    summary: event.summary,
    records
  }

  return {
    id: `${eventId}-summary`,
    title: event.summary ?? 'Event summary',
    timestamp,
    events: [eventItem]
  }
}

const normalizeDateString = (value: unknown, fallback?: string): string => {
  if (typeof value === 'string' && value) {
    return value
  }
  if (typeof value === 'number' && !Number.isNaN(value)) {
    return new Date(value).toISOString()
  }
  if (value instanceof Date) {
    return value.toISOString()
  }
  return fallback ?? new Date().toISOString()
}

export function buildEventSummaryFromRaw(event: any, eventIndex: number): EventSummary {
  if (!event) {
    return mapEvent(
      {
        id: `event-${eventIndex}`,
        start_time: new Date().toISOString(),
        end_time: new Date().toISOString(),
        type: 'event',
        summary: '',
        source_data: []
      },
      eventIndex
    )
  }

  let sourceData = event.sourceData ?? event.source_data ?? []
  if (typeof sourceData === 'string') {
    try {
      sourceData = JSON.parse(sourceData)
    } catch (error) {
      console.warn('[buildEventSummaryFromRaw] Failed to parse sourceData string, using empty array', error)
      sourceData = []
    }
  }

  const normalizedSourceData: ActivityRowRecord[] = Array.isArray(sourceData)
    ? sourceData.map((record: any) => {
        const rawData = typeof record?.data === 'object' && record?.data !== null ? record.data : {}
        const screenshotPath =
          record?.screenshot_path ??
          record?.screenshotPath ??
          rawData?.screenshotPath ??
          rawData?.screenshot_path ??
          null

        return {
          timestamp: normalizeDateString(record?.timestamp, new Date().toISOString()),
          type: typeof record?.type === 'string' && record.type ? record.type : 'unknown_record',
          data: rawData,
          screenshot_path: typeof screenshotPath === 'string' ? screenshotPath : null
        }
      })
    : []

  const normalizedEvent: ActivityRowEvent = {
    id: event.id ?? `event-${eventIndex}`,
    start_time: normalizeDateString(event.startTime ?? event.start_time, new Date().toISOString()),
    end_time: normalizeDateString(
      event.endTime ?? event.end_time ?? event.startTime ?? event.start_time,
      new Date().toISOString()
    ),
    type: typeof event.type === 'string' && event.type ? event.type : 'event',
    summary: event.summary,
    source_data: normalizedSourceData
  }

  return mapEvent(normalizedEvent, eventIndex)
}

// Safe date parsing helper
const parseDate = (dateStr: string | undefined | null): number => {
  if (!dateStr) {
    console.warn(`[parseDate] Invalid date string encountered: "${dateStr}", using current time`)
    return Date.now()
  }
  const parsed = new Date(dateStr).getTime()
  if (isNaN(parsed)) {
    console.warn(`[parseDate] Failed to parse date string: "${dateStr}", using current time`)
    return Date.now()
  }
  return parsed
}

const parseSourceEventIds = (value?: string | null): string[] => {
  if (!value) {
    return []
  }

  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter((item) => item.length > 0)
  }

  const trimmed = value.trim()
  if (!trimmed) {
    return []
  }

  try {
    const parsed = JSON.parse(trimmed)
    if (Array.isArray(parsed)) {
      return parsed.map((item) => String(item)).filter((item) => item.length > 0)
    }
  } catch (error) {
    console.warn('[parseSourceEventIds] Failed to parse source_event_ids JSON', error)
  }

  return []
}

function mapActivity(row: ActivityRow, index: number, includeEvents: boolean = true): Activity {
  const start = parseDate(row.start_time)
  const end = parseDate(row.end_time)

  let eventSummaries: EventSummary[] = []
  if (includeEvents && row.source_events) {
    const rawEvents: ActivityRowEvent[] =
      typeof row.source_events === 'string' ? JSON.parse(row.source_events) : (row.source_events ?? [])
    eventSummaries = rawEvents.map((event, eventIndex) => mapEvent(event, eventIndex))
  }

  const sourceEventIds = parseSourceEventIds(row.source_event_ids)

  return {
    id: row.id ?? `activity-${index}`,
    title: row.title || row.description, // Prefer title, fall back to full description
    description: row.description,
    startTime: start,
    endTime: end,
    sourceEventIds,
    sessionDurationMinutes: undefined,
    topicTags: [],
    createdAt: start,
    updatedAt: start,

    // Backward compatibility
    name: row.title || row.description,
    timestamp: start,
    eventSummaries
  }
}

function buildTimeline(activities: Activity[]): TimelineDay[] {
  const grouped = new Map<string, Activity[]>()

  activities.forEach((activity) => {
    // Use startTime (always present) instead of deprecated timestamp
    const timestamp = activity.timestamp ?? activity.startTime

    // Defensive check for valid timestamp
    if (typeof timestamp !== 'number' || isNaN(timestamp)) {
      console.warn(`[buildTimeline] Invalid activity timestamp: ${timestamp}`, activity.id)
      return
    }

    // Fix timezone issues: derive dates using local time instead of UTC
    const d = new Date(timestamp)
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
    dayActivities.sort((a, b) => {
      const aTime = a.timestamp ?? a.startTime
      const bTime = b.timestamp ?? b.startTime
      return bTime - aTime
    })
    return {
      date,
      activities: dayActivities
    }
  })
}

export async function fetchActivityTimeline(query: TimelineQuery): Promise<TimelineDay[]> {
  const { start, end, limit = 50, offset = 0 } = query
  const db = await resolveDatabase()

  let parameterIndex = 1
  const filters: string[] = []
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

  // Optimization: query only summary data (load source_events when expanding)
  let sql = 'SELECT id, title, description, start_time, end_time, source_event_ids FROM activities'
  if (filters.length > 0) {
    sql += ` WHERE ${filters.join(' AND ')}`
  }
  sql += ' ORDER BY start_time DESC'
  sql += ` LIMIT $${parameterIndex}`
  bindValues.push(limit)
  parameterIndex += 1

  if (offset > 0) {
    sql += ` OFFSET $${parameterIndex}`
    bindValues.push(offset)
  }

  console.debug('[fetchActivityTimeline] Querying summary data, SQL:', sql)
  const rows = await db.select<ActivityRow[]>(sql, bindValues)
  // Do not load eventSummaries (includeEvents = false)
  const activities = rows.map((row, index) => mapActivity(row, index, false))

  return buildTimeline(activities)
}

/**
 * Load a single activity with the full eventSummaries
 * Call when a user expands an activity
 */
export async function fetchActivityDetails(activityId: string): Promise<Activity | null> {
  const db = await resolveDatabase()

  const rows = await db.select<ActivityRow[]>(
    'SELECT id, title, description, start_time, end_time, source_events, source_event_ids FROM activities WHERE id = ?',
    [activityId]
  )

  if (rows.length === 0) {
    console.warn('[fetchActivityDetails] Activity not found:', activityId)
    return null
  }

  const row = rows[0]

  // Check whether source_events is empty
  if (!row.source_events || row.source_events === '[]' || row.source_events === '') {
    console.debug('[fetchActivityDetails] Activity has no event data:', activityId)
    // Return the activity with an empty eventSummaries array
    return mapActivity(row, 0, false)
  }

  console.debug(
    '[fetchActivityDetails] Loading activity details:',
    activityId,
    'Event data length:',
    typeof row.source_events === 'string' ? row.source_events.length : JSON.stringify(row.source_events).length
  )

  return mapActivity(rows[0], 0, true) // includeEvents = true
}
