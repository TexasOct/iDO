// Activity record type definitions - THREE-LAYER ARCHITECTURE

/**
 * Raw record from perception layer (screenshots, keyboard, mouse)
 */
export interface RawRecord {
  id: string
  timestamp: number
  type: string
  content: string
  metadata?: Record<string, unknown>
}

/**
 * ACTION - Fine-grained operation (e.g., "opened file", "wrote code")
 * Extracted from RawRecords every ~4 seconds via LLM
 * Replaces old "Event" concept
 */
export interface Action {
  id: string
  title: string
  description: string
  keywords: string[]
  timestamp: number
  screenshots?: string[]
  createdAt?: number
}

/**
 * EVENT - Medium-grained work segment (e.g., "modified login.py")
 * Aggregated from Actions every 10 minutes
 * Replaces old "Activity" concept
 */
export interface Event {
  id: string
  title: string
  description: string
  startTime: number
  endTime: number
  sourceActionIds: string[]
  createdAt: number

  // Backward compatibility fields
  /** @deprecated Use startTime instead */
  timestamp?: number
  /** @deprecated Use title or description instead */
  summary?: string
  /** @deprecated Three-layer architecture no longer embeds raw records */
  records?: RawRecord[]
}

/**
 * ACTIVITY - Coarse-grained work session (e.g., "implemented login feature")
 * Aggregated from Events every 30 minutes via SessionAgent
 * NEW top layer
 */
export interface Activity {
  id: string
  title: string
  description: string
  startTime: number
  endTime: number
  sourceEventIds: string[]
  sessionDurationMinutes?: number
  topicTags: string[]
  userMergedFromIds?: string[]
  userSplitIntoIds?: string[]
  createdAt: number
  updatedAt: number

  // Backward compatibility fields (for gradual migration)
  /** @deprecated Use title instead */
  name?: string
  /** @deprecated Use startTime instead */
  timestamp?: number
  /** @deprecated Three-layer architecture no longer embeds full event data */
  eventSummaries?: EventSummary[]
}

/**
 * EventSummary for backward compatibility
 */
export interface EventSummary {
  id: string
  title: string
  timestamp: number
  events: LegacyEvent[]
}

/**
 * Timeline day grouping activities
 */
export interface TimelineDay {
  date: string // YYYY-MM-DD
  activities: Activity[]
}

// Legacy types for backward compatibility (DEPRECATED - will be removed in future)
// Use Action/Event/Activity instead

/**
 * @deprecated Use Action instead
 */
export interface LegacyEvent {
  id: string
  startTime: number
  endTime: number
  timestamp: number
  summary?: string
  records: RawRecord[]
}

/**
 * @deprecated Use Event instead
 */
export interface LegacyEventSummary {
  id: string
  title: string
  timestamp: number
  events: LegacyEvent[]
}

/**
 * @deprecated Use Activity instead
 */
export interface LegacyActivity {
  id: string
  title: string
  name: string
  description?: string
  timestamp: number
  startTime: number
  endTime: number
  sourceEventIds: string[]
  eventSummaries: LegacyEventSummary[]
}
