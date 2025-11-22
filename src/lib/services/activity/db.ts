import Database from '@tauri-apps/plugin-sql'
import { appDataDir, appConfigDir, resourceDir, join } from '@tauri-apps/api/path'
import { pyInvoke } from 'tauri-plugin-pytauri-api'
import { TimelineDay, Activity, EventSummary, Event, RawRecord } from '@/lib/types/activity'

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

  // 优先级 1: 从后端 config.toml 获取配置的数据库路径
  console.debug('[activity-db] 优先从后端获取配置的数据库路径')
  const backendPath = await resolvePathFromBackend()
  if (backendPath) {
    console.debug('[activity-db] 后端返回的数据库路径:', backendPath)
    safePush(backendPath)
  }

  // 优先级 2: 标准平台目录
  try {
    const configDir = await appConfigDir()
    const configPath = await join(configDir, 'ido.db')
    console.debug('[activity-db] 标准配置目录路径:', configPath)
    safePush(configPath)
  } catch (error) {
    console.warn('Failed to resolve appConfigDir', error)
  }

  try {
    const dataDir = await appDataDir()
    const dataPath = await join(dataDir, 'ido.db')
    console.debug('[activity-db] 标准数据目录路径:', dataPath)
    safePush(dataPath)
  } catch (error) {
    console.warn('Failed to resolve appDataDir', error)
  }

  // 优先级 3: 开发环境备选相对路径（仅作为最后的回退）
  candidates.push('sqlite:ido.db', 'sqlite:../ido.db', 'sqlite:../../ido.db')

  // 优先级 4: 资源目录（仅作为开发/打包调试用）
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

  console.debug('[activity-db] 数据库候选路径顺序:', candidates.slice(0, 3), '...')
  return candidates
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

  const eventItem: Event = {
    id: eventId,
    startTime,
    endTime,
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
      console.warn('[buildEventSummaryFromRaw] 无法解析 sourceData 字符串，使用空数组', error)
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

// 安全的日期解析辅助函数
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
    title: row.title || row.description, // 使用title字段，如果为空则使用完整的description
    name: row.title || row.description,
    description: row.description,
    timestamp: start,
    startTime: start,
    endTime: end,
    sourceEventIds,
    eventSummaries
  }
}

function buildTimeline(activities: Activity[]): TimelineDay[] {
  const grouped = new Map<string, Activity[]>()

  activities.forEach((activity) => {
    // Defensive check for valid timestamp
    if (typeof activity.timestamp !== 'number' || isNaN(activity.timestamp)) {
      console.warn(`[buildTimeline] Invalid activity timestamp: ${activity.timestamp}`, activity.id)
      return
    }

    // 修复时区问题：使用本地时间而不是 UTC 时间来提取日期
    const d = new Date(activity.timestamp)
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

  // 优化：只查询摘要数据，不加载 source_events（在展开时才加载）
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

  console.debug('[fetchActivityTimeline] 查询摘要数据，SQL:', sql)
  const rows = await db.select<ActivityRow[]>(sql, bindValues)
  // 不加载 eventSummaries（includeEvents = false）
  const activities = rows.map((row, index) => mapActivity(row, index, false))

  return buildTimeline(activities)
}

/**
 * 加载单个活动的详细数据（包括完整的 eventSummaries）
 * 当用户展开活动时调用此函数
 */
export async function fetchActivityDetails(activityId: string): Promise<Activity | null> {
  const db = await resolveDatabase()

  const rows = await db.select<ActivityRow[]>(
    'SELECT id, title, description, start_time, end_time, source_events, source_event_ids FROM activities WHERE id = ?',
    [activityId]
  )

  if (rows.length === 0) {
    console.warn('[fetchActivityDetails] 活动未找到:', activityId)
    return null
  }

  const row = rows[0]

  // 检查 source_events 是否为空
  if (!row.source_events || row.source_events === '[]' || row.source_events === '') {
    console.debug('[fetchActivityDetails] 活动暂无事件数据:', activityId)
    // 返回没有事件的活动（eventSummaries 为空数组）
    return mapActivity(row, 0, false)
  }

  console.debug(
    '[fetchActivityDetails] 加载活动详细数据:',
    activityId,
    '事件数据长度:',
    typeof row.source_events === 'string' ? row.source_events.length : JSON.stringify(row.source_events).length
  )

  return mapActivity(rows[0], 0, true) // includeEvents = true
}
