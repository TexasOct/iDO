/**
 * Activity service utility functions
 */

import { EventSummary, RawRecord, LegacyEvent } from '@/lib/types/activity'

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

/**
 * Build EventSummary from raw event data
 * Used for parsing backend event data into frontend format
 */
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
