import Database from '@tauri-apps/plugin-sql'
import { appDataDir, appConfigDir, resourceDir, join } from '@tauri-apps/api/path'
import { pyInvoke } from 'tauri-plugin-pytauri-api'
import { TimelineDay, Activity, EventSummary, Event, RawRecord } from '@/lib/types/activity'

interface ActivityRow {
  id: string
  description: string
  start_time: string
  end_time: string
  source_events: string | ActivityRowEvent[]
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
    console.debug('[activity-db] 尝试连接数据库', connection)
    const db = await Database.load(connection)
    const hasActivitiesTable = await db
      .select<{ name: string }[]>("SELECT name FROM sqlite_master WHERE type = 'table' AND name = $1", ['activities'])
      .catch(() => [])
    if (hasActivitiesTable.length > 0) {
      console.debug('[activity-db] 使用数据库连接', connection)
      return db
    }
    await db.close().catch(() => false)
    console.debug('[activity-db] 数据库缺少 activities 表，关闭连接', connection)
    return null
  } catch (error) {
    console.warn('Failed to connect to database', connection, error)
    return null
  }
}

async function buildCandidateConnections(): Promise<string[]> {
  const candidates = new Set<string>(['sqlite:rewind.db', 'sqlite:../rewind.db', 'sqlite:../../rewind.db'])

  const safePush = (value?: string | null) => {
    if (value) {
      if (value.startsWith('sqlite:')) {
        candidates.add(value)
        candidates.add(`${value}?mode=ro`)
      } else {
        candidates.add(`sqlite:${value}`)
        candidates.add(`sqlite:${value}?mode=ro`)
      }
    }
  }

  const backendPath = await resolvePathFromBackend()
  if (backendPath) {
    safePush(backendPath)
  }

  try {
    const dataDir = await appDataDir()
    safePush(await join(dataDir, 'rewind.db'))
  } catch (error) {
    console.warn('Failed to resolve appDataDir', error)
  }

  try {
    const configDir = await appConfigDir()
    safePush(await join(configDir, 'rewind.db'))
  } catch (error) {
    console.warn('Failed to resolve appConfigDir', error)
  }

  // TODO: 后续 tauri 打包之后，rewind.db 会放到一个固定的相对路径里面，这个地方后续还需要修改
  try {
    const resDir = await resourceDir()
    safePush(await join(resDir, '..', 'rewind.db'))
    safePush(await join(resDir, '..', '..', 'rewind.db'))
    safePush(await join(resDir, '..', '..', 'src-tauri', 'rewind.db'))
    safePush(await join(resDir, '..', '..', '..', 'rewind.db'))
    safePush(await join(resDir, '..', '..', '..', 'src-tauri', 'rewind.db'))
    safePush(await join(resDir, '..', '..', '..', '..', 'rewind.db'))
    safePush(await join(resDir, '..', '..', '..', '..', 'src-tauri', 'rewind.db'))
  } catch (error) {
    console.warn('Failed to resolve resourceDir', error)
  }

  return Array.from(candidates)
}

async function resolvePathFromBackend(): Promise<string | null> {
  try {
    const response = await pyInvoke<{
      success: boolean
      data?: { path?: string }
    }>('get_database_path', {})

    if (response?.success && response.data?.path) {
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

      throw new Error('未找到可用的活动数据库，请确认后端已生成数据')
    })()
  }

  return dbInstance
}

function mapRecord(eventId: string, record: ActivityRowRecord, index: number): RawRecord {
  const timestamp = new Date(record.timestamp).getTime()
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
      return `按键：${data.key}`
    }
    if (typeof data.action === 'string') {
      return `键盘操作：${data.action}`
    }
    return '键盘输入'
  }

  if (type === 'mouse_record') {
    const action = typeof data.action === 'string' ? data.action : '鼠标操作'
    const button = typeof data.button === 'string' ? `（${data.button}）` : ''
    return `${action}${button}`
  }

  if (type === 'screenshot_record') {
    return '截屏捕获'
  }

  if (typeof data.summary === 'string') {
    return data.summary
  }
  if (typeof data.title === 'string') {
    return data.title
  }

  return `${type} 事件`
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

function formatEventType(type: string): string {
  const mapping: Record<string, string> = {
    keyboard_record: '键盘事件',
    mouse_record: '鼠标事件',
    screenshot_record: '截图事件'
  }
  return mapping[type] ?? type
}

function mapEvent(event: ActivityRowEvent, eventIndex: number): EventSummary {
  const eventId = event.id ?? `event-${eventIndex}`
  const timestamp = new Date(event.start_time).getTime()
  const records = (event.source_data ?? []).map((record, index) => mapRecord(eventId, record, index))

  const eventItem: Event = {
    id: eventId,
    type: formatEventType(event.type),
    timestamp,
    summary: event.summary,
    records
  }

  return {
    id: `${eventId}-summary`,
    title: event.summary ?? '事件摘要',
    timestamp,
    events: [eventItem]
  }
}

function mapActivity(row: ActivityRow, index: number): Activity {
  const start = new Date(row.start_time).getTime()
  const end = new Date(row.end_time).getTime()
  const rawEvents: ActivityRowEvent[] =
    typeof row.source_events === 'string' ? JSON.parse(row.source_events) : (row.source_events ?? [])

  const eventSummaries = rawEvents.map((event, eventIndex) => mapEvent(event, eventIndex))

  return {
    id: row.id ?? `activity-${index}`,
    name: row.description,
    description: row.description,
    timestamp: start,
    startTime: start,
    endTime: end,
    eventSummaries
  }
}

function buildTimeline(activities: Activity[]): TimelineDay[] {
  const grouped = new Map<string, Activity[]>()

  activities.forEach((activity) => {
    const date = new Date(activity.timestamp).toISOString().split('T')[0]
    if (!grouped.has(date)) {
      grouped.set(date, [])
    }
    grouped.get(date)!.push(activity)
  })

  const sortedDates = Array.from(grouped.keys()).sort((a, b) => (a > b ? -1 : 1))

  return sortedDates.map((date) => {
    const dayActivities = grouped.get(date) ?? []
    dayActivities.sort((a, b) => b.timestamp - a.timestamp)
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

  let sql = 'SELECT id, description, start_time, end_time, source_events FROM activities'
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

  const rows = await db.select<ActivityRow[]>(sql, bindValues)
  const activities = rows.map((row, index) => mapActivity(row, index))

  return buildTimeline(activities)
}
