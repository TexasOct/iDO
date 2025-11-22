// 活动记录相关类型定义

export interface RawRecord {
  id: string
  timestamp: number
  type: string
  content: string
  metadata?: Record<string, unknown>
}

export interface Event {
  id: string
  startTime: number
  endTime: number
  timestamp: number
  summary?: string
  records: RawRecord[]
}

export interface EventSummary {
  id: string
  title: string
  timestamp: number
  events: Event[]
}

export interface Activity {
  id: string
  title: string
  name: string
  description?: string
  timestamp: number
  startTime: number
  endTime: number
  sourceEventIds: string[]
  eventSummaries: EventSummary[]
}

export interface TimelineDay {
  date: string // YYYY-MM-DD
  activities: Activity[]
}
