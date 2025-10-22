import { create } from 'zustand'
import { fetchActivityTimeline } from '@/lib/services/activity/db'
import { TimelineDay } from '@/lib/types/activity'

interface ActivityState {
  timelineData: TimelineDay[]
  selectedDate: string | null
  expandedItems: Set<string> // 记录展开的节点 ID
  loading: boolean
  error: string | null

  // Actions
  fetchTimelineData: (dateRange: { start?: string; end?: string }) => Promise<void>
  setSelectedDate: (date: string) => void
  toggleExpanded: (id: string) => void
  expandAll: () => void
  collapseAll: () => void
}

export const useActivityStore = create<ActivityState>((set, get) => ({
  timelineData: [],
  selectedDate: null,
  expandedItems: new Set(),
  loading: false,
  error: null,

  fetchTimelineData: async (dateRange) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchActivityTimeline(dateRange)

      set({
        timelineData: data,
        loading: false,
        expandedItems: new Set()
      })
    } catch (error) {
      set({ error: (error as Error).message, loading: false })
    }
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

  collapseAll: () => set({ expandedItems: new Set() })
}))
