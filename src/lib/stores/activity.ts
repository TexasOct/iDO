import { create } from 'zustand'
import { fetchActivityTimeline, fetchActivityDetails } from '@/lib/services/activity/db'
import { fetchActivityCountByDate } from '@/lib/services/activity'
import { TimelineDay } from '@/lib/types/activity'

interface ActivityState {
  timelineData: TimelineDay[]
  selectedDate: string | null
  expandedItems: Set<string> // 记录展开的节点 ID
  currentMaxVersion: number // 当前客户端已同步的最大版本号（用于增量更新）
  isAtLatest: boolean // 用户是否在最新位置（能接收增量更新）
  loading: boolean
  loadingMore: boolean // 加载更多时的加载状态
  loadingActivityDetails: Set<string> // 正在加载详细数据的活动 ID
  loadedActivityDetails: Set<string> // 已加载详细数据的活动 ID
  error: string | null
  hasMoreTop: boolean // 顶部是否还有更多数据
  hasMoreBottom: boolean // 底部是否还有更多数据
  topOffset: number // 顶部已加载的活动偏移量（用于计算下次加载的起点）
  bottomOffset: number // 底部已加载的活动偏移量（用于计算下次加载的起点）
  dateCountMap: Record<string, number> // 数据库中每天的实际活动总数（不分页）

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
  setIsAtLatest: (isAtLatest: boolean) => void
  getActualDayCount: (date: string) => number // 获取该天在数据库中的实际活动总数
}

const MAX_TIMELINE_ITEMS = 100 // 最多保持100个元素

export const useActivityStore = create<ActivityState>((set, get) => ({
  timelineData: [],
  selectedDate: null,
  expandedItems: new Set(),
  currentMaxVersion: 0,
  isAtLatest: true, // 初始化时认为在最新位置
  loading: false,
  loadingMore: false,
  loadingActivityDetails: new Set(),
  loadedActivityDetails: new Set(),
  error: null,
  hasMoreTop: true,
  hasMoreBottom: true,
  topOffset: 0, // 顶部已加载的活动偏移量
  bottomOffset: 0, // 底部已加载的活动偏移量
  dateCountMap: {},

  fetchTimelineData: async (options = {}) => {
    const { limit = 15 } = options
    set({ loading: true, error: null })
    try {
      console.debug('[fetchTimelineData] 初始化加载，limit:', limit, '个活动')
      const data = await fetchActivityTimeline({ limit, offset: 0 })

      const totalActivities = data.reduce((sum, day) => sum + day.activities.length, 0)

      console.debug('[fetchTimelineData] 初始化完成 -', {
        天数: data.length,
        活动数: totalActivities,
        hasMoreBottom: totalActivities > 0
      })

      set({
        timelineData: data,
        loading: false,
        expandedItems: new Set(),
        currentMaxVersion: 0,
        isAtLatest: true, // 初始化时在最新位置
        hasMoreTop: false, // 初始化时已在最新位置，向上无更多数据
        hasMoreBottom: totalActivities === limit, // 如果返回了请求的完整数量，说明可能还有更多
        topOffset: 0, // 初始化时已在顶部
        bottomOffset: totalActivities // 初始化时已加载的活动数
      })

      // 异步获取每天的实际总数（不阻塞UI）
      get().fetchActivityCountByDate()
    } catch (error) {
      console.error('[fetchTimelineData] 加载失败:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  fetchMoreTimelineDataTop: async () => {
    const { timelineData, loadingMore, hasMoreTop, topOffset } = get()

    if (loadingMore || !hasMoreTop || timelineData.length === 0) {
      console.warn('[fetchMoreTimelineDataTop] 提前返回 -', { loadingMore, hasMoreTop })
      return
    }

    set({ loadingMore: true, isAtLatest: false }) // 向上滚动，不在最新位置

    try {
      const LIMIT = 15
      // 基于活动偏移量加载更新的活动
      const offset = topOffset

      console.debug('[fetchMoreTimelineDataTop] 加载顶部活动，offset:', offset)

      const moreData = await fetchActivityTimeline({ limit: LIMIT, offset })

      if (moreData.length === 0) {
        console.warn('[fetchMoreTimelineDataTop] 没有更新的活动')
        set({ hasMoreTop: false, loadingMore: false })
        return
      }

      const newActivityCount = moreData.reduce((sum, day) => sum + day.activities.length, 0)
      console.warn('[fetchMoreTimelineDataTop] ✅ 加载成功 -', newActivityCount, '个新活动')

      set((state) => {
        let merged = [...state.timelineData]

        // 在顶部插入新活动（去重处理）
        moreData.forEach((newDay) => {
          const existingIndex = merged.findIndex((d) => d.date === newDay.date)
          if (existingIndex >= 0) {
            // 创建现有活动 ID 的 Set 用于去重
            const existingIds = new Set(merged[existingIndex].activities.map((a) => a.id))
            // 只添加不存在的新活动
            const uniqueNewActivities = newDay.activities.filter((a) => !existingIds.has(a.id))
            merged[existingIndex].activities = [...uniqueNewActivities, ...merged[existingIndex].activities]
          } else {
            merged.unshift(newDay)
          }
        })

        // 超过最大限制时，从底部卸载日期块
        if (merged.length > MAX_TIMELINE_ITEMS) {
          const removedFromBottom = merged.length - MAX_TIMELINE_ITEMS
          console.debug('[fetchMoreTimelineDataTop] 超过日期块限制，从底部移除', removedFromBottom, '个日期块')
          merged = merged.slice(0, merged.length - removedFromBottom)
        }

        return {
          timelineData: merged,
          loadingMore: false,
          hasMoreTop: newActivityCount === LIMIT, // 如果返回了完整的数量，说明可能还有更多
          topOffset: state.topOffset + newActivityCount
        }
      })
    } catch (error) {
      console.error('[fetchMoreTimelineDataTop] 加载失败:', error)
      set({ error: (error as Error).message, loadingMore: false })
    }
  },

  fetchMoreTimelineDataBottom: async () => {
    const { timelineData, loadingMore, hasMoreBottom, bottomOffset } = get()

    if (loadingMore || !hasMoreBottom || timelineData.length === 0) {
      console.warn('[fetchMoreTimelineDataBottom] 提前返回 -', { loadingMore, hasMoreBottom })
      return
    }

    set({ loadingMore: true })

    try {
      const LIMIT = 15
      // 基于活动偏移量加载更旧的活动
      const offset = bottomOffset

      console.debug('[fetchMoreTimelineDataBottom] 加载底部活动，offset:', offset)

      const moreData = await fetchActivityTimeline({ limit: LIMIT, offset })

      if (moreData.length === 0) {
        console.warn('[fetchMoreTimelineDataBottom] 没有更旧的活动')
        set({ hasMoreBottom: false, loadingMore: false })
        return
      }

      const newActivityCount = moreData.reduce((sum, day) => sum + day.activities.length, 0)
      console.warn('[fetchMoreTimelineDataBottom] ✅ 加载成功 -', newActivityCount, '个旧活动')

      set((state) => {
        let merged = [...state.timelineData]
        // 在底部追加更旧的活动
        moreData.forEach((newDay) => {
          const existingIndex = merged.findIndex((d) => d.date === newDay.date)
          if (existingIndex >= 0) {
            // 创建现有活动 ID 的 Set 用于去重
            const existingIds = new Set(merged[existingIndex].activities.map((a) => a.id))
            // 只添加不存在的新活动
            const uniqueNewActivities = newDay.activities.filter((a) => !existingIds.has(a.id))
            merged[existingIndex].activities = [...merged[existingIndex].activities, ...uniqueNewActivities]
          } else {
            merged.push(newDay)
          }
        })

        // 超过最大限制时，从顶部卸载日期块
        if (merged.length > MAX_TIMELINE_ITEMS) {
          const toRemove = merged.length - MAX_TIMELINE_ITEMS
          console.debug('[fetchMoreTimelineDataBottom] 超过日期块限制，从顶部移除', toRemove, '个日期块')
          merged = merged.slice(toRemove)
        }

        return {
          timelineData: merged,
          loadingMore: false,
          hasMoreBottom: newActivityCount === LIMIT, // 如果返回了完整的数量，说明可能还有更多
          bottomOffset: state.bottomOffset + newActivityCount
        }
      })
    } catch (error) {
      console.error('[fetchMoreTimelineDataBottom] 加载失败:', error)
      set({ error: (error as Error).message, loadingMore: false })
    }
  },

  fetchActivityCountByDate: async () => {
    try {
      console.debug('[fetchActivityCountByDate] 开始获取每天的实际活动总数')
      const dateCountMap = await fetchActivityCountByDate()

      console.debug('[fetchActivityCountByDate] ✅ 获取成功，共', Object.keys(dateCountMap).length, '天')

      set({ dateCountMap })
    } catch (error) {
      console.error('[fetchActivityCountByDate] 获取失败:', error)
    }
  },

  loadActivityDetails: async (activityId: string) => {
    const { loadedActivityDetails, loadingActivityDetails } = get()

    // 如果已加载过，直接返回（避免重复加载）
    if (loadedActivityDetails.has(activityId)) {
      console.debug('[loadActivityDetails] 活动详情已缓存，跳过加载:', activityId)
      return
    }

    // 如果正在加载，直接返回（避免重复请求）
    if (loadingActivityDetails.has(activityId)) {
      console.debug('[loadActivityDetails] 活动详情正在加载，跳过:', activityId)
      return
    }

    try {
      console.debug('[loadActivityDetails] 开始加载活动详情:', activityId)

      // 标记为正在加载
      set((state) => ({
        loadingActivityDetails: new Set(state.loadingActivityDetails).add(activityId)
      }))

      // 从数据库加载详细数据
      const detailedActivity = await fetchActivityDetails(activityId)

      if (!detailedActivity) {
        console.warn('[loadActivityDetails] 活动未找到:', activityId)
        return
      }

      console.debug('[loadActivityDetails] ✅ 加载成功，事件数:', detailedActivity.eventSummaries?.length ?? 0)

      // 更新时间线数据中的活动
      set((state) => {
        const newTimelineData = state.timelineData.map((day) => ({
          ...day,
          activities: day.activities.map((activity) =>
            activity.id === activityId
              ? {
                  ...activity,
                  eventSummaries: detailedActivity.eventSummaries
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
      console.error('[loadActivityDetails] 加载失败:', error)
      // 移除正在加载标记
      set((state) => {
        const newLoadingActivityDetails = new Set(state.loadingActivityDetails)
        newLoadingActivityDetails.delete(activityId)
        return { loadingActivityDetails: newLoadingActivityDetails }
      })
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

  collapseAll: () => set({ expandedItems: new Set() }),

  setCurrentMaxVersion: (version) => set({ currentMaxVersion: version }),

  setTimelineData: (updater) =>
    set((state) => {
      const newData = updater(state.timelineData)
      return { timelineData: newData }
    }),

  setIsAtLatest: (isAtLatest) => set({ isAtLatest }),

  getActualDayCount: (date: string) => {
    const { dateCountMap } = get()
    return dateCountMap[date] || 0
  }
}))
