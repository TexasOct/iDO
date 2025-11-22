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

const MAX_TIMELINE_ITEMS = 100 // 最多保持100个元素

const safeParseTimestamp = (value?: string | null, fallback?: number): number => {
  if (!value) {
    return fallback ?? Date.now()
  }
  const parsed = new Date(value).getTime()
  if (Number.isNaN(parsed)) {
    console.warn(`[activityStore] 无法解析时间戳 "${value}", 使用备用值`)
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
  removeActivity: (activityId: string) => void
  setIsAtLatest: (isAtLatest: boolean) => void
  applyActivityUpdate: (activity: ActivityUpdatePayload) => ActivityUpdateResult
  getActualDayCount: (date: string) => number // 获取该天在数据库中的实际活动总数
}

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
        loadedActivityDetails: new Set(), // 清空已加载的详情缓存
        loadingActivityDetails: new Set(), // 清空正在加载的标记
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
        // 1. 使用 Map 合并数据，确保按日期去重
        const dateMap = new Map<string, any>()

        // 先添加新数据
        moreData.forEach((day) => {
          dateMap.set(day.date, { ...day })
        })

        // 再合并旧数据
        state.timelineData.forEach((day) => {
          if (dateMap.has(day.date)) {
            const existingDay = dateMap.get(day.date)
            // 合并活动并去重（基于 id）
            const existingIds = new Set(existingDay.activities.map((a: Activity) => a.id))
            const newActivities = day.activities.filter((a: Activity) => !existingIds.has(a.id))
            // 新活动在前（因为是从顶部加载的）
            existingDay.activities = [...existingDay.activities, ...newActivities]
          } else {
            dateMap.set(day.date, { ...day })
          }
        })

        // 2. 转换为数组并排序（新的在前）
        let merged = Array.from(dateMap.values()).sort((a, b) => (a.date > b.date ? -1 : 1))

        // 3. 滑动窗口：超过限制时从底部卸载（保持最新的数据）
        if (merged.length > MAX_TIMELINE_ITEMS) {
          const removedFromBottom = merged.length - MAX_TIMELINE_ITEMS
          console.debug(
            `[fetchMoreTimelineDataTop] 滑动窗口：超过限制（最多 ${MAX_TIMELINE_ITEMS} 个日期块），从底部移除 ${removedFromBottom} 个`
          )
          // 保留最新的 MAX_TIMELINE_ITEMS 个日期块
          merged = merged.slice(0, MAX_TIMELINE_ITEMS)

          // 记录被移除的日期，用于调试
          const removedDates = merged.slice(MAX_TIMELINE_ITEMS).map((day) => day.date)
          if (removedDates.length > 0) {
            console.debug('[fetchMoreTimelineDataTop] 被移除的日期:', removedDates)
          }
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
        // 1. 使用 Map 合并数据，确保按日期去重
        const dateMap = new Map<string, any>()

        // 先添加旧数据
        state.timelineData.forEach((day) => {
          dateMap.set(day.date, { ...day })
        })

        // 再合并新数据（底部追加的数据）
        moreData.forEach((day) => {
          if (dateMap.has(day.date)) {
            const existingDay = dateMap.get(day.date)
            // 合并活动并去重（基于 id）
            const existingIds = new Set(existingDay.activities.map((a: Activity) => a.id))
            const newActivities = day.activities.filter((a: Activity) => !existingIds.has(a.id))
            // 追加到末尾（因为是旧的活动）
            existingDay.activities = [...existingDay.activities, ...newActivities]
          } else {
            dateMap.set(day.date, { ...day })
          }
        })

        // 2. 转换为数组并排序（新的在前）
        let merged = Array.from(dateMap.values()).sort((a, b) => (a.date > b.date ? -1 : 1))

        // 3. 滑动窗口：超过限制时从顶部卸载（保持最新的数据）
        if (merged.length > MAX_TIMELINE_ITEMS) {
          const toRemove = merged.length - MAX_TIMELINE_ITEMS
          console.debug(
            `[fetchMoreTimelineDataBottom] 滑动窗口：超过限制（最多 ${MAX_TIMELINE_ITEMS} 个日期块），从顶部移除 ${toRemove} 个`
          )
          // 记录被移除的日期，用于调试
          const removedDates = merged.slice(0, toRemove).map((day) => day.date)
          if (removedDates.length > 0) {
            console.debug('[fetchMoreTimelineDataBottom] 被移除的日期:', removedDates)
          }
          // 保留最新的 MAX_TIMELINE_ITEMS 个日期块
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
    const { loadedActivityDetails, loadingActivityDetails, timelineData } = get()

    // 如果正在加载，直接返回（避免重复请求）
    if (loadingActivityDetails.has(activityId)) {
      console.debug('[loadActivityDetails] 活动详情正在加载，跳过:', activityId)
      return
    }

    // 检查当前活动的事件数据
    let currentActivity: Activity | undefined
    for (const day of timelineData) {
      currentActivity = day.activities.find((a) => a.id === activityId)
      if (currentActivity) break
    }

    // 如果已加载过且有事件数据，直接返回
    if (loadedActivityDetails.has(activityId) && currentActivity?.eventSummaries?.length) {
      console.debug('[loadActivityDetails] 活动详情已缓存，跳过加载:', activityId)
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
        // 标记为已加载（避免重复请求）
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
          '[loadActivityDetails] 本地活动缺少事件数据，使用 API 按 ID 加载:',
          detailedActivity.sourceEventIds.length
        )
        try {
          const details = await fetchEventsByIds(detailedActivity.sourceEventIds)
          eventSummaries = convertEventDetailsToSummaries(details)
          console.debug('[loadActivityDetails] ✅ 通过 API 加载事件成功:', eventSummaries.length)
        } catch (error) {
          console.error('[loadActivityDetails] 通过事件 ID 加载详情失败:', error)
        }
      }

      console.debug('[loadActivityDetails] ✅ 加载成功，事件数:', eventSummaries.length)

      // 更新时间线数据中的活动
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
      console.error('[loadActivityDetails] 加载失败:', error)
      // 移除正在加载标记
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
        console.warn('[applyActivityUpdate] 未在时间线中找到活动:', activity.id)
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
