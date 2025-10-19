// 活动记录相关类型定义

export interface RawRecord {
  id: string
  timestamp: number
  content: string
  metadata?: Record<string, any>
}

export interface Event {
  id: string
  type: string
  timestamp: number
  records: RawRecord[]
  summary?: string
}

export interface EventSummary {
  id: string
  title: string
  timestamp: number
  events: Event[]
}

export interface Activity {
  id: string
  name: string
  timestamp: number
  eventSummaries: EventSummary[]
}

export interface TimelineDay {
  date: string // YYYY-MM-DD
  activities: Activity[]
}
