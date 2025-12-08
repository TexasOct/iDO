import { create } from 'zustand'
import { fetchActivityTimeline, fetchEventsByActivityId, fetchActionsByEventId } from '@/lib/services/activity/api'
import { fetchActivityCountByDate } from '@/lib/services/activity'
import { TimelineDay, Activity, Event, Action } from '@/lib/types/activity'
// Note: All activity data access now uses backend API handlers instead of direct SQL queries
// Migration complete: db.ts → api.ts, three-layer-db.ts → api.ts

type TimelineActivity = Activity & { version?: number; isNew?: boolean }

interface ActivityUpdatePayload {
  id: string
  title?: string
  description?: string
  startTime?: string
  endTime?: string
  sourceEvents?: any[]
  version?: number
  createdAt?: string
}

interface ActivityUpdateResult {
  updated: boolean
  dateChanged: boolean
}

const MAX_TIMELINE_ITEMS = 100 // Keep at most 100 entries

const safeParseTimestamp = (value?: string | null, fallback?: number): number => {
  if (!value) {
    return fallback ?? Date.now()
  }
  const parsed = new Date(value).getTime()
  if (Number.isNaN(parsed)) {
    console.warn(`[activityStore] Unable to parse timestamp "${value}", using fallback`)
    return fallback ?? Date.now()
  }
  return parsed
}

const toDateKey = (timestamp: number): string => {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

interface ActivityState {
  timelineData: TimelineDay[]
  selectedDate: string | null
  currentMaxVersion: number // Highest version synced on the client (for incremental updates)
  cacheVersion: number // Increment to force dependent views to drop cached day data
  isAtLatest: boolean // Whether the user is at the latest position (can accept incremental updates)
  loading: boolean
  loadingMore: boolean // Loading flag when fetching more data
  error: string | null
  hasMoreTop: boolean // Whether additional data exists above
  hasMoreBottom: boolean // Whether additional data exists below
  topOffset: number // Offset for activities already loaded at the top
  bottomOffset: number // Offset for activities already loaded at the bottom
  dateCountMap: Record<string, number> // Actual per-day counts from the database (non-paged)

  // Three-layer architecture drill-down state
  expandedActivityId: string | null // Currently expanded activity for drill-down
  expandedEvents: Event[] // Events loaded for the expanded activity
  loadingEvents: boolean // Loading state for events
  expandedEventId: string | null // Currently expanded event for drill-down
  expandedActions: Action[] // Actions loaded for the expanded event
  loadingActions: boolean // Loading state for actions

  // Batch selection state
  selectedActivities: Set<string> // Selected activity IDs for batch operations
  selectionMode: boolean // Whether selection mode is active

  // Actions
  fetchTimelineData: (options?: { limit?: number }) => Promise<void>
  fetchMoreTimelineDataTop: () => Promise<void>
  fetchMoreTimelineDataBottom: () => Promise<void>
  fetchActivityCountByDate: () => Promise<void>
  setSelectedDate: (date: string) => void
  setCurrentMaxVersion: (version: number) => void
  setTimelineData: (updater: (prev: TimelineDay[]) => TimelineDay[]) => void
  invalidateActivitiesByDateRange: (startDate: string, endDate: string) => void
  removeActivity: (activityId: string) => void
  setIsAtLatest: (isAtLatest: boolean) => void
  applyActivityUpdate: (activity: ActivityUpdatePayload) => ActivityUpdateResult
  getActualDayCount: (date: string) => number // Get the DB-backed total for the given day

  // Three-layer architecture drill-down actions
  fetchEventsByActivity: (activityId: string) => Promise<void>
  fetchActionsByEvent: (eventId: string) => Promise<void>
  toggleActivityDrillDown: (activityId: string) => void
  toggleEventDrillDown: (eventId: string) => void
  clearDrillDown: () => void

  // Batch selection actions
  toggleSelectionMode: () => void
  toggleActivitySelection: (activityId: string) => void
  clearSelection: () => void
  selectAllVisibleActivities: () => void
}

export const useActivityStore = create<ActivityState>((set, get) => ({
  timelineData: [],
  selectedDate: null,
  currentMaxVersion: 0,
  cacheVersion: 0,
  isAtLatest: true, // Assume we start at the latest position
  loading: false,
  loadingMore: false,
  error: null,
  hasMoreTop: true,
  hasMoreBottom: true,
  topOffset: 0, // Offset for top-loaded activities
  bottomOffset: 0, // Offset for bottom-loaded activities
  dateCountMap: {},

  // Three-layer architecture drill-down state
  expandedActivityId: null,
  expandedEvents: [],
  loadingEvents: false,
  expandedEventId: null,
  expandedActions: [],
  loadingActions: false,

  // Batch selection state
  selectedActivities: new Set(),
  selectionMode: false,

  fetchTimelineData: async (options = {}) => {
    const { limit = 15 } = options
    set({ loading: true, error: null })
    try {
      console.debug('[fetchTimelineData] Initial load, limit:', limit, 'activities')

      // Unified API call (no longer needs feature flag distinction)
      const data = await fetchActivityTimeline({ limit, offset: 0 })

      const totalActivities = data.reduce((sum, day) => sum + day.activities.length, 0)

      console.debug('[fetchTimelineData] Initial load complete -', {
        days: data.length,
        activities: totalActivities,
        hasMoreBottom: totalActivities > 0
      })

      set({
        timelineData: data,
        loading: false,
        currentMaxVersion: 0,
        isAtLatest: true, // Start at the latest position
        hasMoreTop: false, // Already at the latest position, nothing above
        hasMoreBottom: totalActivities === limit, // Full page implies more data remains
        topOffset: 0, // Start at the top
        bottomOffset: totalActivities // Activities loaded at init
      })

      // Fetch per-day counts asynchronously to avoid blocking the UI
      get().fetchActivityCountByDate()
    } catch (error) {
      console.error('[fetchTimelineData] Load failed:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  fetchMoreTimelineDataTop: async () => {
    const { timelineData, loadingMore, hasMoreTop, topOffset } = get()

    if (loadingMore || !hasMoreTop || timelineData.length === 0) {
      console.warn('[fetchMoreTimelineDataTop] Early return -', { loadingMore, hasMoreTop })
      return
    }

    set({ loadingMore: true, isAtLatest: false }) // Scrolling up means we are no longer at the latest position

    try {
      const LIMIT = 15
      // Load newer activities based on offsets
      const offset = topOffset

      console.debug('[fetchMoreTimelineDataTop] Loading top segment, offset:', offset)

      // Unified API call (no longer needs feature flag distinction)
      const moreData = await fetchActivityTimeline({ limit: LIMIT, offset })

      if (moreData.length === 0) {
        console.warn('[fetchMoreTimelineDataTop] No newer activities')
        set({ hasMoreTop: false, loadingMore: false })
        return
      }

      const newActivityCount = moreData.reduce((sum, day) => sum + day.activities.length, 0)
      console.warn('[fetchMoreTimelineDataTop] ✅ Loaded', newActivityCount, 'new activities')

      set((state) => {
        // 1. Use a Map to merge and dedupe by date
        const dateMap = new Map<string, any>()

        // Add new data first
        moreData.forEach((day) => {
          dateMap.set(day.date, { ...day })
        })

        // Then merge the existing data
        state.timelineData.forEach((day) => {
          if (dateMap.has(day.date)) {
            const existingDay = dateMap.get(day.date)
            // Merge activities deduped by id
            const existingIds = new Set(existingDay.activities.map((a: Activity) => a.id))
            const newActivities = day.activities.filter((a: Activity) => !existingIds.has(a.id))
            // Keep newer activities first (loaded from the top)
            existingDay.activities = [...existingDay.activities, ...newActivities]
          } else {
            dateMap.set(day.date, { ...day })
          }
        })

        // 2. Convert to an array and sort (newer first)
        let merged = Array.from(dateMap.values()).sort((a, b) => (a.date > b.date ? -1 : 1))

        // 3. Sliding window: drop entries from the bottom if over limit
        if (merged.length > MAX_TIMELINE_ITEMS) {
          const removedFromBottom = merged.length - MAX_TIMELINE_ITEMS
          console.debug(
            `[fetchMoreTimelineDataTop] Sliding window: exceeded limit (${MAX_TIMELINE_ITEMS} days max), removed ${removedFromBottom} from bottom`
          )
          // Keep the newest MAX_TIMELINE_ITEMS day blocks
          merged = merged.slice(0, MAX_TIMELINE_ITEMS)

          // Record removed dates for debugging
          const removedDates = merged.slice(MAX_TIMELINE_ITEMS).map((day) => day.date)
          if (removedDates.length > 0) {
            console.debug('[fetchMoreTimelineDataTop] Removed dates:', removedDates)
          }
        }

        return {
          timelineData: merged,
          loadingMore: false,
          hasMoreTop: newActivityCount === LIMIT, // Full batch implies more above
          topOffset: state.topOffset + newActivityCount
        }
      })
    } catch (error) {
      console.error('[fetchMoreTimelineDataTop] Load failed:', error)
      set({ error: (error as Error).message, loadingMore: false })
    }
  },

  fetchMoreTimelineDataBottom: async () => {
    const { timelineData, loadingMore, hasMoreBottom, bottomOffset } = get()

    if (loadingMore || !hasMoreBottom || timelineData.length === 0) {
      console.warn('[fetchMoreTimelineDataBottom] Early return -', { loadingMore, hasMoreBottom })
      return
    }

    set({ loadingMore: true })

    try {
      const LIMIT = 15
      // Load older activities based on offsets
      const offset = bottomOffset

      console.debug('[fetchMoreTimelineDataBottom] Loading bottom segment, offset:', offset)

      // Unified API call (no longer needs feature flag distinction)
      const moreData = await fetchActivityTimeline({ limit: LIMIT, offset })

      if (moreData.length === 0) {
        console.warn('[fetchMoreTimelineDataBottom] No older activities')
        set({ hasMoreBottom: false, loadingMore: false })
        return
      }

      const newActivityCount = moreData.reduce((sum, day) => sum + day.activities.length, 0)
      console.warn('[fetchMoreTimelineDataBottom] ✅ Loaded', newActivityCount, 'older activities')

      set((state) => {
        // 1. Use a Map to merge and dedupe by date
        const dateMap = new Map<string, any>()

        // Add older data first
        state.timelineData.forEach((day) => {
          dateMap.set(day.date, { ...day })
        })

        // Merge the existing data (appended at the bottom)
        moreData.forEach((day) => {
          if (dateMap.has(day.date)) {
            const existingDay = dateMap.get(day.date)
            // Merge activities deduped by id
            const existingIds = new Set(existingDay.activities.map((a: Activity) => a.id))
            const newActivities = day.activities.filter((a: Activity) => !existingIds.has(a.id))
            // Append to the end because the activities are older
            existingDay.activities = [...existingDay.activities, ...newActivities]
          } else {
            dateMap.set(day.date, { ...day })
          }
        })

        // 2. Convert to an array and sort (newer first)
        let merged = Array.from(dateMap.values()).sort((a, b) => (a.date > b.date ? -1 : 1))

        // 3. Sliding window: drop from the top if we exceed the limit
        if (merged.length > MAX_TIMELINE_ITEMS) {
          const toRemove = merged.length - MAX_TIMELINE_ITEMS
          console.debug(
            `[fetchMoreTimelineDataBottom] Sliding window: exceeded limit (${MAX_TIMELINE_ITEMS} days max), removed ${toRemove} from top`
          )
          // Record removed dates for debugging
          const removedDates = merged.slice(0, toRemove).map((day) => day.date)
          if (removedDates.length > 0) {
            console.debug('[fetchMoreTimelineDataBottom] Removed dates:', removedDates)
          }
          // Keep the newest MAX_TIMELINE_ITEMS day blocks
          merged = merged.slice(toRemove)
        }

        return {
          timelineData: merged,
          loadingMore: false,
          hasMoreBottom: newActivityCount === LIMIT, // Full batch implies more below
          bottomOffset: state.bottomOffset + newActivityCount
        }
      })
    } catch (error) {
      console.error('[fetchMoreTimelineDataBottom] Load failed:', error)
      set({ error: (error as Error).message, loadingMore: false })
    }
  },

  fetchActivityCountByDate: async () => {
    try {
      console.debug('[fetchActivityCountByDate] Fetching actual daily totals')
      const dateCountMap = await fetchActivityCountByDate()

      console.debug('[fetchActivityCountByDate] ✅ Success, days loaded:', Object.keys(dateCountMap).length)

      set({ dateCountMap })
    } catch (error) {
      console.error('[fetchActivityCountByDate] Fetch failed:', error)
    }
  },

  applyActivityUpdate: (activity) => {
    let result: ActivityUpdateResult = { updated: false, dateChanged: false }

    set((state) => {
      const { timelineData, currentMaxVersion } = state

      let locatedDayIndex = -1
      let locatedActivityIndex = -1

      for (let i = 0; i < timelineData.length; i += 1) {
        const idx = timelineData[i].activities.findIndex((item) => item.id === activity.id)
        if (idx !== -1) {
          locatedDayIndex = i
          locatedActivityIndex = idx
          break
        }
      }

      if (locatedDayIndex === -1 || locatedActivityIndex === -1) {
        console.warn('[applyActivityUpdate] Activity not found in timeline:', activity.id)
        return {}
      }

      const currentDay = timelineData[locatedDayIndex]
      const currentActivity = currentDay.activities[locatedActivityIndex] as TimelineActivity

      const nextTitle = activity.title ?? currentActivity.title
      const nextDescription = activity.description ?? currentActivity.description
      const nextName = activity.title ?? activity.description ?? currentActivity.name
      const nextStartTime = activity.startTime
        ? safeParseTimestamp(activity.startTime, currentActivity.startTime)
        : currentActivity.startTime
      const nextEndTime = activity.endTime
        ? safeParseTimestamp(activity.endTime, currentActivity.endTime ?? nextStartTime)
        : (currentActivity.endTime ?? nextStartTime)
      const nextTimestamp = nextStartTime

      const nextVersion = typeof activity.version === 'number' ? activity.version : currentActivity.version

      const newDateKey = toDateKey(nextTimestamp)
      const originalDateKey = currentDay.date

      const hasMeaningfulChange =
        nextTitle !== currentActivity.title ||
        nextDescription !== currentActivity.description ||
        nextTitle !== currentActivity.title ||
        nextName !== currentActivity.name ||
        nextTimestamp !== currentActivity.timestamp ||
        nextEndTime !== currentActivity.endTime ||
        newDateKey !== originalDateKey ||
        (typeof nextVersion === 'number' && nextVersion !== currentActivity.version)

      if (!hasMeaningfulChange) {
        return {}
      }

      const updatedActivity: TimelineActivity = {
        ...currentActivity,
        title: nextTitle,
        name: nextName,
        description: nextDescription,
        startTime: nextStartTime,
        endTime: nextEndTime,
        timestamp: nextTimestamp,
        version: nextVersion,
        isNew: false
      }

      let nextTimeline = [...timelineData]

      if (newDateKey === originalDateKey) {
        const nextActivities = [...currentDay.activities]
        nextActivities[locatedActivityIndex] = updatedActivity
        nextActivities.sort((a, b) => {
          const aTime = a.timestamp ?? a.startTime
          const bTime = b.timestamp ?? b.startTime
          return bTime - aTime
        })
        nextTimeline[locatedDayIndex] = {
          ...currentDay,
          activities: nextActivities
        }
      } else {
        const remainingActivities = currentDay.activities.filter((item) => item.id !== activity.id)
        if (remainingActivities.length > 0) {
          nextTimeline[locatedDayIndex] = {
            ...currentDay,
            activities: remainingActivities
          }
        } else {
          nextTimeline.splice(locatedDayIndex, 1)
        }

        const existingDayIndex = nextTimeline.findIndex((day) => day.date === newDateKey)
        if (existingDayIndex !== -1) {
          const day = nextTimeline[existingDayIndex]
          const activities = [...day.activities, updatedActivity]
          activities.sort((a, b) => {
            const aTime = a.timestamp ?? a.startTime
            const bTime = b.timestamp ?? b.startTime
            return bTime - aTime
          })
          nextTimeline[existingDayIndex] = {
            ...day,
            activities
          }
        } else {
          nextTimeline.push({
            date: newDateKey,
            activities: [updatedActivity]
          })
        }
      }

      nextTimeline = nextTimeline.sort((a, b) => (a.date > b.date ? -1 : 1))

      if (nextTimeline.length > MAX_TIMELINE_ITEMS) {
        nextTimeline = nextTimeline.slice(0, MAX_TIMELINE_ITEMS)
      }

      result = { updated: true, dateChanged: newDateKey !== originalDateKey }

      const partial: Partial<ActivityState> = {
        timelineData: nextTimeline
      }

      if (typeof nextVersion === 'number' && nextVersion > currentMaxVersion) {
        partial.currentMaxVersion = nextVersion
      }

      return partial
    })

    return result
  },

  setSelectedDate: (date) => set({ selectedDate: date }),

  setCurrentMaxVersion: (version) => set({ currentMaxVersion: version }),

  setTimelineData: (updater) =>
    set((state) => {
      const newData = updater(state.timelineData)
      return { timelineData: newData }
    }),

  invalidateActivitiesByDateRange: (startDate, endDate) =>
    set((state) => {
      const removedIds = new Set<string>()

      state.timelineData.forEach((day) => {
        if (day.date >= startDate && day.date <= endDate) {
          day.activities.forEach((activity) => removedIds.add(activity.id))
        }
      })

      const filteredTimeline = state.timelineData.filter((day) => day.date < startDate || day.date > endDate)

      const nextDateCountMap = { ...state.dateCountMap }
      Object.keys(nextDateCountMap).forEach((date) => {
        if (date >= startDate && date <= endDate) {
          delete nextDateCountMap[date]
        }
      })

      const totalActivities = filteredTimeline.reduce((sum, day) => sum + day.activities.length, 0)

      return {
        timelineData: filteredTimeline,
        currentMaxVersion: 0,
        cacheVersion: state.cacheVersion + 1,
        isAtLatest: true,
        hasMoreTop: true,
        hasMoreBottom: true,
        topOffset: 0,
        bottomOffset: totalActivities,
        dateCountMap: nextDateCountMap
      }
    }),

  removeActivity: (activityId) =>
    set((state) => {
      let hasChanges = false

      const nextTimeline: TimelineDay[] = []
      state.timelineData.forEach((day) => {
        const filteredActivities = day.activities.filter((activity) => activity.id !== activityId)
        if (filteredActivities.length !== day.activities.length) {
          hasChanges = true
        }
        if (filteredActivities.length > 0) {
          const nextDay =
            filteredActivities.length === day.activities.length ? day : { ...day, activities: filteredActivities }
          nextTimeline.push(nextDay)
        }
      })

      if (!hasChanges) {
        return {}
      }

      return {
        timelineData: nextTimeline
      }
    }),

  setIsAtLatest: (isAtLatest) => set({ isAtLatest }),

  getActualDayCount: (date: string) => {
    const { dateCountMap } = get()
    return dateCountMap[date] || 0
  },

  // Three-layer architecture drill-down actions
  fetchEventsByActivity: async (activityId: string) => {
    const { loadingEvents } = get()

    if (loadingEvents) {
      console.debug('[fetchEventsByActivity] Already loading events, skip')
      return
    }

    set({
      loadingEvents: true,
      expandedActivityId: activityId,
      expandedEvents: [],
      expandedEventId: null,
      expandedActions: []
    })

    try {
      console.debug('[fetchEventsByActivity] Fetching events for activity:', activityId)

      const events = await fetchEventsByActivityId(activityId)

      console.debug('[fetchEventsByActivity] ✅ Loaded events:', events.length)

      set({ expandedEvents: events, loadingEvents: false })
    } catch (error) {
      console.error('[fetchEventsByActivity] Failed to load events:', error)
      set({ loadingEvents: false, error: (error as Error).message })
    }
  },

  fetchActionsByEvent: async (eventId: string) => {
    const { loadingActions } = get()

    if (loadingActions) {
      console.debug('[fetchActionsByEvent] Already loading actions, skip')
      return
    }

    set({ loadingActions: true, expandedEventId: eventId, expandedActions: [] })

    try {
      console.debug('[fetchActionsByEvent] Fetching actions for event:', eventId)

      const actions = await fetchActionsByEventId(eventId)

      console.debug('[fetchActionsByEvent] ✅ Loaded actions:', actions.length)

      set({ expandedActions: actions, loadingActions: false })
    } catch (error) {
      console.error('[fetchActionsByEvent] Failed to load actions:', error)
      set({ loadingActions: false, error: (error as Error).message })
    }
  },

  toggleActivityDrillDown: (activityId: string) => {
    const { expandedActivityId } = get()

    if (expandedActivityId === activityId) {
      // Collapse
      console.debug('[toggleActivityDrillDown] Collapsing activity:', activityId)
      set({ expandedActivityId: null, expandedEvents: [], expandedEventId: null, expandedActions: [] })
    } else {
      // Expand and fetch events
      console.debug('[toggleActivityDrillDown] Expanding activity:', activityId)
      get().fetchEventsByActivity(activityId)
    }
  },

  toggleEventDrillDown: (eventId: string) => {
    const { expandedEventId } = get()

    if (expandedEventId === eventId) {
      // Collapse
      console.debug('[toggleEventDrillDown] Collapsing event:', eventId)
      set({ expandedEventId: null, expandedActions: [] })
    } else {
      // Expand and fetch actions
      console.debug('[toggleEventDrillDown] Expanding event:', eventId)
      get().fetchActionsByEvent(eventId)
    }
  },

  clearDrillDown: () => {
    console.debug('[clearDrillDown] Clearing all drill-down state')
    set({
      expandedActivityId: null,
      expandedEvents: [],
      expandedEventId: null,
      expandedActions: []
    })
  },

  // Batch selection actions
  toggleSelectionMode: () => {
    const { selectionMode } = get()
    console.debug(`[toggleSelectionMode] ${selectionMode ? 'Disabling' : 'Enabling'} selection mode`)

    // Clear selection when disabling selection mode
    if (selectionMode) {
      set({ selectionMode: false, selectedActivities: new Set() })
    } else {
      set({ selectionMode: true })
    }
  },

  toggleActivitySelection: (activityId: string) => {
    const { selectedActivities } = get()
    const newSelection = new Set(selectedActivities)

    if (newSelection.has(activityId)) {
      newSelection.delete(activityId)
      console.debug(`[toggleActivitySelection] Deselected activity: ${activityId}`)
    } else {
      newSelection.add(activityId)
      console.debug(`[toggleActivitySelection] Selected activity: ${activityId}`)
    }

    set({ selectedActivities: newSelection })
  },

  clearSelection: () => {
    console.debug('[clearSelection] Clearing all selected activities')
    set({ selectedActivities: new Set() })
  },

  selectAllVisibleActivities: () => {
    const { timelineData, selectedDate } = get()

    // Get all activities from the selected date
    const targetDay = timelineData.find((day) => day.date === selectedDate)
    if (!targetDay) {
      console.debug('[selectAllVisibleActivities] No activities found for selected date')
      return
    }

    const allActivityIds = new Set(targetDay.activities.map((activity) => activity.id))
    console.debug(`[selectAllVisibleActivities] Selected ${allActivityIds.size} activities`)
    set({ selectedActivities: allActivityIds })
  }
}))
