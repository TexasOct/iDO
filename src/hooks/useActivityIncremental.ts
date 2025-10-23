import { useCallback, useEffect, useRef } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { useActivityCreated } from './use-tauri-events'
import { fetchActivitiesIncremental } from '@/lib/services/activity'

const MAX_TIMELINE_ITEMS = 100

/**
 * Hook 用于订阅后端活动更新事件并执行增量更新
 * 使用滑动窗口策略：当窗口在顶部时，接收到新活动事件后拉取最新数据
 *
 * 工作流程：
 * 1. 后端发送 activity-created 事件（活动被持久化）
 * 2. 检查当前窗口是否在顶部（topOffset === 0）
 * 3. 如果在顶部，调用 fetchActivitiesIncremental 拉取新活动
 * 4. 将新活动合并到时间线顶部，维持最多 100 个日期块的限制
 * 5. 更新版本号和日期计数
 */
export function useActivityIncremental() {
  // 分别订阅各个字段，避免选择器返回新对象
  // const timelineData = useActivityStore((state) => state.timelineData)
  const topOffset = useActivityStore((state) => state.topOffset)
  const currentMaxVersion = useActivityStore((state) => state.currentMaxVersion)
  const setTimelineData = useActivityStore((state) => state.setTimelineData)
  const setCurrentMaxVersion = useActivityStore((state) => state.setCurrentMaxVersion)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)

  // 使用 ref 存储状态，避免依赖项频繁变化导致处理函数重新创建
  const stateRef = useRef({ topOffset, currentMaxVersion })

  // 同步 ref 中的状态
  useEffect(() => {
    stateRef.current = { topOffset, currentMaxVersion }
  }, [topOffset, currentMaxVersion])

  /**
   * 处理新的活动创建事件
   * 滑动窗口策略：仅当窗口在顶部时，才拉取增量更新
   */
  const handleActivityCreated = useCallback(
    async (payload: any) => {
      if (!payload || !payload.data) {
        console.warn('[useActivityIncremental] 收到的活动数据格式不正确', payload)
        return
      }

      const { topOffset, currentMaxVersion } = stateRef.current

      console.debug('[useActivityIncremental] 收到新活动事件', {
        activityId: payload.data.id,
        topOffset,
        isWindowAtTop: topOffset === 0
      })

      // 如果窗口不在顶部，则不拉取增量更新（避免打断用户的滚动）
      if (topOffset !== 0) {
        console.debug('[useActivityIncremental] 窗口不在顶部，跳过增量更新')
        return
      }

      // 窗口在顶部，拉取增量更新
      try {
        const newTimelineData = await fetchActivitiesIncremental(currentMaxVersion, 15)

        if (newTimelineData.length === 0) {
          console.debug('[useActivityIncremental] 没有新的活动数据')
          return
        }

        console.debug('[useActivityIncremental] 获取增量更新成功，合并到时间线', {
          newDays: newTimelineData.length,
          totalActivities: newTimelineData.reduce((sum, day) => sum + day.activities.length, 0)
        })

        // 合并新数据到时间线
        setTimelineData((prevData) => {
          let merged = [...newTimelineData, ...prevData]

          // 去重处理：移除重复的日期块
          const seenDates = new Set<string>()
          merged = merged.filter((day) => {
            if (seenDates.has(day.date)) {
              return false
            }
            seenDates.add(day.date)
            return true
          })

          // 超过限制时，从底部卸载日期块
          if (merged.length > MAX_TIMELINE_ITEMS) {
            const removedCount = merged.length - MAX_TIMELINE_ITEMS
            console.debug('[useActivityIncremental] 超过日期块限制（最多100个），从底部移除', removedCount, '个日期块')
            merged = merged.slice(0, MAX_TIMELINE_ITEMS)
          }

          return merged
        })

        // 更新版本号
        const maxVersion = newTimelineData.reduce(
          (max, day) => Math.max(max, ...day.activities.map((a: any) => a.version || 0)),
          currentMaxVersion
        )
        setCurrentMaxVersion(maxVersion)

        // 异步更新日期计数（不阻塞 UI）
        fetchActivityCountByDate()
      } catch (error) {
        console.error('[useActivityIncremental] 增量更新失败:', error)
      }
    },
    [setTimelineData, setCurrentMaxVersion, fetchActivityCountByDate]
  )

  // 订阅后端的 activity-created 事件
  useActivityCreated(handleActivityCreated)
}
