import { create } from 'zustand'
import { fetchActivityTimeline, fetchActivityDetails } from '@/lib/services/activity/db'
import { fetchActivityCountByDate } from '@/lib/services/activity'
import { ActivityEventDetail, fetchEventsByIds } from '@/lib/services/activity/item'
import { TimelineDay, Activity, EventSummary, RawRecord } from '@/lib/types/activity'

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

const buildRecordsFromEventDetail = (detail: ActivityEventDetail): RawRecord[] => {
  const records: RawRecord[] = []

  if (detail.summary || detail.keywords.length > 0) {
    records.push({
      id: `${detail.id}-summary-record`,
      timestamp: detail.timestamp,
      type: 'summary',
      content: detail.summary || '',
      metadata: detail.keywords.length > 0 ? { keywords: detail.keywords } : undefined
    })
  }

  detail.screenshots.forEach((path, index) => {
    records.push({
      id: `${detail.id}-screenshot-${index}`,
      timestamp: detail.timestamp + index + 1,
      type: 'screenshot',
      content: '',
      metadata: { action: 'capture', screenshotPath: path }
    })
  })

  if (records.length === 0) {
    records.push({
      id: `${detail.id}-empty`,
      timestamp: detail.timestamp,
      type: 'summary',
      content: ''
    })
  }

  return records
}

const convertEventDetailsToSummaries = (details: ActivityEventDetail[]): EventSummary[] => {
  return details.map((detail, index) => ({
    id: `${detail.id}-summary-${index}`,
    title: detail.summary || '',
    timestamp: detail.timestamp,
    events: [
      {
        id: detail.id,
        startTime: detail.timestamp,
        endTime: detail.timestamp,
        timestamp: detail.timestamp,
        summary: detail.summary,
        records: buildRecordsFromEventDetail(detail)
      }
    ]
  }))
}

interface ActivityState {
  timelineData: TimelineDay[]
  selectedDate: string | null
  expandedItems: Set<string> // Track expanded node IDs
  currentMaxVersion: number // Highest version synced on the client (for incremental updates)
  isAtLatest: boolean // Whether the user is at the latest position (can accept incremental updates)
  loading: boolean
  loadingMore: boolean // Loading flag when fetching more data
  loadingActivityDetails: Set<string> // Activities currently loading details
  loadedActivityDetails: Set<string> // Activities whose details have been loaded
  error: string | null
  hasMoreTop: boolean // Whether additional data exists above
  hasMoreBottom: boolean // Whether additional data exists below
  topOffset: number // Offset for activities already loaded at the top
  bottomOffset: number // Offset for activities already loaded at the bottom
  dateCountMap: Record<string, number> // Actual per-day counts from the database (non-paged)

  // Actions
  fetchTimelineData: (options?: { limit?: number }) => Promise<void>
  fetchMoreTimelineDataTop: () => Promise<void>
  fetchMoreTimelineDataBottom: () => Promise<void>
  fetchActivityCountByDate: () => Promise<void>
  loadActivityDetails: (activityId: string) => Promise<void>
  setSelectedDate: (date: string) => void
  toggleExpanded: (id: string) => void
  expandAll: () => void
  collapseAll: () => void
  setCurrentMaxVersion: (version: number) => void
  setTimelineData: (updater: (prev: TimelineDay[]) => TimelineDay[]) => void
  removeActivity: (activityId: string) => void
  setIsAtLatest: (isAtLatest: boolean) => void
  applyActivityUpdate: (activity: ActivityUpdatePayload) => ActivityUpdateResult
  getActualDayCount: (date: string) => number // Get the DB-backed total for the given day
}

export const useActivityStore = create<ActivityState>((set, get) => ({
  timelineData: [],
  selectedDate: null,
  expandedItems: new Set(),
  currentMaxVersion: 0,
  isAtLatest: true, // Assume we start at the latest position
  loading: false,
  loadingMore: false,
  loadingActivityDetails: new Set(),
  loadedActivityDetails: new Set(),
  error: null,
  hasMoreTop: true,
  hasMoreBottom: true,
  topOffset: 0, // Offset for top-loaded activities
  bottomOffset: 0, // Offset for bottom-loaded activities
  dateCountMap: {},

  fetchTimelineData: async (options = {}) => {
    const { limit = 15 } = options
    set({ loading: true, error: null })
    try {
      console.debug('[fetchTimelineData] Initial load, limit:', limit, 'activities')
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
        expandedItems: new Set(),
        loadedActivityDetails: new Set(), // Clear any cached details
        loadingActivityDetails: new Set(), // Reset loading markers
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

  loadActivityDetails: async (activityId: string) => {
    const { loadedActivityDetails, loadingActivityDetails, timelineData } = get()

    // If loading, exit early to avoid duplicate requests
    if (loadingActivityDetails.has(activityId)) {
      console.debug('[loadActivityDetails] Details already loading, skip:', activityId)
      return
    }

    // Inspect the current activity event data
    let currentActivity: Activity | undefined
    for (const day of timelineData) {
      currentActivity = day.activities.find((a) => a.id === activityId)
      if (currentActivity) break
    }

    // If event data already exists, return immediately
    if (loadedActivityDetails.has(activityId) && currentActivity?.eventSummaries?.length) {
      console.debug('[loadActivityDetails] Details cached, skip load:', activityId)
      return
    }

    try {
      console.debug('[loadActivityDetails] Start loading activity details:', activityId)

      // Mark as loading
      set((state) => ({
        loadingActivityDetails: new Set(state.loadingActivityDetails).add(activityId)
      }))

      // Load details from the database
      const detailedActivity = await fetchActivityDetails(activityId)

      if (!detailedActivity) {
        console.warn('[loadActivityDetails] Activity not found:', activityId)
        // Mark as loaded to avoid duplicate requests
        set((state) => {
          const newLoadedActivityDetails = new Set(state.loadedActivityDetails).add(activityId)
          const newLoadingActivityDetails = new Set(state.loadingActivityDetails)
          newLoadingActivityDetails.delete(activityId)
          return {
            loadedActivityDetails: newLoadedActivityDetails,
            loadingActivityDetails: newLoadingActivityDetails
          }
        })
        return
      }

      let eventSummaries = detailedActivity.eventSummaries || []

      if (eventSummaries.length === 0 && detailedActivity.sourceEventIds.length > 0) {
        console.debug(
          '[loadActivityDetails] Local activity lacks event data, fetching by ID via API:',
          detailedActivity.sourceEventIds.length
        )
        try {
          const details = await fetchEventsByIds(detailedActivity.sourceEventIds)
          eventSummaries = convertEventDetailsToSummaries(details)
          console.debug('[loadActivityDetails] ✅ Loaded events via API:', eventSummaries.length)
        } catch (error) {
          console.error('[loadActivityDetails] Failed to load details via event IDs:', error)
        }
      }

      console.debug('[loadActivityDetails] ✅ Load successful, events:', eventSummaries.length)

      // Update the activity inside the timeline data
      set((state) => {
        const newTimelineData = state.timelineData.map((day) => ({
          ...day,
          activities: day.activities.map((activity) =>
            activity.id === activityId
              ? {
                  ...activity,
                  eventSummaries,
                  sourceEventIds: detailedActivity.sourceEventIds
                }
              : activity
          )
        }))

        const newLoadedActivityDetails = new Set(state.loadedActivityDetails).add(activityId)
        const newLoadingActivityDetails = new Set(state.loadingActivityDetails)
        newLoadingActivityDetails.delete(activityId)

        return {
          timelineData: newTimelineData,
          loadedActivityDetails: newLoadedActivityDetails,
          loadingActivityDetails: newLoadingActivityDetails
        }
      })
    } catch (error) {
      console.error('[loadActivityDetails] Load failed:', error)
      // Clear the loading marker
      set((state) => {
        const newLoadingActivityDetails = new Set(state.loadingActivityDetails)
        newLoadingActivityDetails.delete(activityId)
        return { loadingActivityDetails: newLoadingActivityDetails }
      })
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
        nextActivities.sort((a, b) => b.timestamp - a.timestamp)
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
          activities.sort((a, b) => b.timestamp - a.timestamp)
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

  toggleExpanded: (id) =>
    set((state) => {
      const newExpanded = new Set(state.expandedItems)
      if (newExpanded.has(id)) {
        newExpanded.delete(id)
      } else {
        newExpanded.add(id)
      }
      return { expandedItems: newExpanded }
    }),

  expandAll: () => {
    const allIds = new Set<string>()
    const { timelineData } = get()
    timelineData.forEach((day) => {
      day.activities.forEach((activity) => {
        allIds.add(activity.id)
        activity.eventSummaries.forEach((summary) => {
          allIds.add(summary.id)
          summary.events.forEach((event) => {
            allIds.add(event.id)
          })
        })
      })
    })
    set({ expandedItems: allIds })
  },

  collapseAll: () => set({ expandedItems: new Set() }),

  setCurrentMaxVersion: (version) => set({ currentMaxVersion: version }),

  setTimelineData: (updater) =>
    set((state) => {
      const newData = updater(state.timelineData)
      return { timelineData: newData }
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

      const nextExpanded = new Set(state.expandedItems)
      nextExpanded.delete(activityId)

      const nextLoadingDetails = new Set(state.loadingActivityDetails)
      nextLoadingDetails.delete(activityId)

      const nextLoadedDetails = new Set(state.loadedActivityDetails)
      nextLoadedDetails.delete(activityId)

      return {
        timelineData: nextTimeline,
        expandedItems: nextExpanded,
        loadingActivityDetails: nextLoadingDetails,
        loadedActivityDetails: nextLoadedDetails
      }
    }),

  setIsAtLatest: (isAtLatest) => set({ isAtLatest }),

  getActualDayCount: (date: string) => {
    const { dateCountMap } = get()
    return dateCountMap[date] || 0
  }
}))
