import { useCallback, useEffect, useRef, useState } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { useActivityCreated } from './use-tauri-events'
import { fetchActivitiesIncremental } from '@/lib/services/activity'

const MAX_TIMELINE_ITEMS = 100
const MAX_RETRY_ATTEMPTS = 3
const RETRY_DELAYS = [1000, 2000, 4000] // 指数退避
const HEALTH_CHECK_INTERVAL = 30000 // 30秒健康检查
const SYNC_TIMEOUT = 10000 // 10秒同步超时

interface SyncState {
  isHealthy: boolean
  lastSyncTime: number
  consecutiveFailures: number
  pendingUpdates: number
}

/**
 * 活动同步 Hook
 * 集成增量更新、错误恢复、备用策略等功能
 */
export function useActivitySync() {
  // 基础状态
  const isAtLatest = useActivityStore((state) => state.isAtLatest)
  const currentMaxVersion = useActivityStore((state) => state.currentMaxVersion)
  const setTimelineData = useActivityStore((state) => state.setTimelineData)
  const setCurrentMaxVersion = useActivityStore((state) => state.setCurrentMaxVersion)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)
  const fetchTimelineData = useActivityStore((state) => state.fetchTimelineData)

  // 同步状态
  const [syncState, setSyncState] = useState<SyncState>({
    isHealthy: true,
    lastSyncTime: Date.now(),
    consecutiveFailures: 0,
    pendingUpdates: 0
  })

  // 使用 ref 存储状态，避免依赖项频繁变化
  const stateRef = useRef({ isAtLatest, currentMaxVersion })
  const syncStateRef = useRef<SyncState>(syncState) // 添加 syncState ref，确保处理函数中总能获取最新值
  const retryTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map())
  const healthCheckIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // 同步 ref 中的状态
  useEffect(() => {
    stateRef.current = { isAtLatest, currentMaxVersion }
  }, [isAtLatest, currentMaxVersion])

  // 同步 syncState ref
  useEffect(() => {
    syncStateRef.current = syncState
  }, [syncState])

  // 健康检查机制
  useEffect(() => {
    const performHealthCheck = async () => {
      try {
        await fetchActivitiesIncremental(currentMaxVersion, 1)

        setSyncState((prev) => ({
          ...prev,
          isHealthy: true,
          lastSyncTime: Date.now(),
          consecutiveFailures: 0
        }))

        console.debug('[useActivitySync] 健康检查通过')
      } catch (error) {
        console.warn('[useActivitySync] 健康检查失败:', error)

        setSyncState((prev) => ({
          ...prev,
          isHealthy: false,
          consecutiveFailures: prev.consecutiveFailures + 1
        }))
      }
    }

    // 启动健康检查
    healthCheckIntervalRef.current = setInterval(performHealthCheck, HEALTH_CHECK_INTERVAL)

    // 立即执行一次健康检查
    performHealthCheck()

    return () => {
      if (healthCheckIntervalRef.current) {
        clearInterval(healthCheckIntervalRef.current)
      }
    }
  }, [currentMaxVersion])

  // 清理重试计时器
  useEffect(() => {
    return () => {
      retryTimeoutsRef.current.forEach((timeout) => clearTimeout(timeout))
      retryTimeoutsRef.current.clear()
    }
  }, [])

  // 带重试的增量更新函数
  const fetchIncrementalWithRetry = useCallback(
    async (version: number, limit: number, attempt: number = 0): Promise<any[]> => {
      const operationId = `fetch-${version}-${Date.now()}`

      try {
        console.debug(`[useActivitySync] 尝试获取增量更新 (尝试 ${attempt + 1}/${MAX_RETRY_ATTEMPTS})`)

        // 设置超时
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error('同步超时')), SYNC_TIMEOUT)
        })

        const dataPromise = fetchActivitiesIncremental(version, limit)
        const result = await Promise.race([dataPromise, timeoutPromise])

        // 成功时清理重试计时器
        const existingTimeout = retryTimeoutsRef.current.get(operationId)
        if (existingTimeout) {
          clearTimeout(existingTimeout)
          retryTimeoutsRef.current.delete(operationId)
        }

        setSyncState((prev) => ({
          ...prev,
          isHealthy: true,
          lastSyncTime: Date.now(),
          consecutiveFailures: 0
        }))

        return result
      } catch (error) {
        console.error(`[useActivitySync] 增量更新失败 (尝试 ${attempt + 1}):`, error)

        if (attempt < MAX_RETRY_ATTEMPTS - 1) {
          const delay = RETRY_DELAYS[attempt] || RETRY_DELAYS[RETRY_DELAYS.length - 1]
          console.debug(`[useActivitySync] ${delay}ms 后重试`)

          return new Promise((resolve, reject) => {
            const timeout = setTimeout(async () => {
              try {
                const result = await fetchIncrementalWithRetry(version, limit, attempt + 1)
                resolve(result)
              } catch (retryError) {
                reject(retryError)
              }
            }, delay)

            retryTimeoutsRef.current.set(operationId, timeout)
          })
        } else {
          // 所有重试都失败了
          setSyncState((prev) => ({
            ...prev,
            isHealthy: false,
            consecutiveFailures: prev.consecutiveFailures + 1
          }))

          throw error
        }
      }
    },
    []
  )

  // 备用策略：全量刷新
  const performFullRefresh = useCallback(async () => {
    console.warn('[useActivitySync] 启用备用策略：全量刷新')

    try {
      // 重置版本号，强制获取最新数据
      setCurrentMaxVersion(0)

      // 执行全量刷新
      await fetchTimelineData({ limit: 50 })

      console.debug('[useActivitySync] 全量刷新成功')
      return true
    } catch (error) {
      console.error('[useActivitySync] 全量刷新失败:', error)
      return false
    }
  }, [fetchTimelineData, setCurrentMaxVersion])

  // 部分刷新策略
  const performPartialRefresh = useCallback(async () => {
    console.warn('[useActivitySync] 启用部分刷新策略')

    try {
      await fetchTimelineData({ limit: 20 })
      console.debug('[useActivitySync] 部分刷新成功')
      return true
    } catch (error) {
      console.error('[useActivitySync] 部分刷新失败:', error)
      return false
    }
  }, [fetchTimelineData])

  // 数据清理策略
  const performDataCleanup = useCallback(async () => {
    console.warn('[useActivitySync] 启用数据清理策略')

    try {
      // 清理时间线数据，重新开始
      setTimelineData(() => [])
      setCurrentMaxVersion(0)

      // 重新加载数据
      await fetchTimelineData({ limit: 15 })

      console.debug('[useActivitySync] 数据清理完成')
      return true
    } catch (error) {
      console.error('[useActivitySync] 数据清理失败:', error)
      return false
    }
  }, [setTimelineData, setCurrentMaxVersion, fetchTimelineData])

  // 智能通知系统
  const showNotification = useCallback((activityCount: number, isRetry: boolean = false) => {
    const notification = document.createElement('div')
    const notificationClass = isRetry
      ? 'fixed top-4 right-4 z-50 transform rounded-lg bg-orange-500 px-4 py-3 text-white shadow-lg transition-all duration-300 translate-x-full'
      : 'fixed top-4 right-4 z-50 transform rounded-lg bg-blue-500 px-4 py-3 text-white shadow-lg transition-all duration-300 translate-x-full'

    notification.className = notificationClass
    notification.innerHTML = `
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-5 5-5-5h5v-5a7.5 7.5 0 1 0-15 0v5h5l-5 5-5-5h5v-5a7.5 7.5 0 1 1 15 0v5z"></path>
          </svg>
          <div class="h-2 w-2 animate-pulse rounded-full bg-white"></div>
        </div>
        <div class="flex-1">
          <p class="text-sm font-medium">${isRetry ? '重试同步' : '有新活动'}</p>
          <p class="text-xs opacity-90">${activityCount} 个新活动${isRetry ? '正在重试同步' : '已添加'}</p>
        </div>
        <div class="flex items-center gap-1">
          <button class="rounded bg-white/20 px-2 py-1 text-xs transition-colors hover:bg-white/30" onclick="this.parentElement.parentElement.parentElement.remove()">查看</button>
          <button class="p-1 text-white/70 transition-colors hover:text-white" onclick="this.parentElement.parentElement.parentElement.remove()">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>
    `

    document.body.appendChild(notification)

    // 显示动画
    setTimeout(() => {
      notification.classList.remove('translate-x-full')
    }, 100)

    // 自动隐藏
    setTimeout(
      () => {
        notification.classList.add('translate-x-full')
        setTimeout(() => {
          if (notification.parentElement) {
            notification.remove()
          }
        }, 300)
      },
      isRetry ? 3000 : 5000
    )
  }, [])

  // 更新时间线的函数
  const updateTimelineWithNewData = useCallback(
    async (newTimelineData: any[]) => {
      try {
        setSyncState((prev) => ({ ...prev, pendingUpdates: prev.pendingUpdates + 1 }))

        // 高效合并新数据到时间线顶部
        setTimelineData((prevData) => {
          const dateMap = new Map<string, any>()

          // 先添加现有数据
          prevData.forEach((day) => {
            dateMap.set(day.date, { ...day })
          })

          // 再合并新数据
          newTimelineData.forEach((day) => {
            if (dateMap.has(day.date)) {
              const existingDay = dateMap.get(day.date)
              const existingIds = new Set(existingDay.activities.map((a: any) => a.id))
              const newActivities = day.activities.filter((a: any) => !existingIds.has(a.id))
              existingDay.activities = [...newActivities, ...existingDay.activities]
            } else {
              dateMap.set(day.date, { ...day })
            }
          })

          // 转换为数组并排序
          let merged = Array.from(dateMap.values()).sort((a, b) => (a.date > b.date ? -1 : 1))

          // 滑动窗口
          if (merged.length > MAX_TIMELINE_ITEMS) {
            const removedCount = merged.length - MAX_TIMELINE_ITEMS
            console.debug(`[useActivitySync] 滑动窗口：移除 ${removedCount} 个旧日期块`)
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

        // 异步更新日期计数
        fetchActivityCountByDate()

        setSyncState((prev) => ({
          ...prev,
          pendingUpdates: Math.max(0, prev.pendingUpdates - 1),
          lastSyncTime: Date.now()
        }))

        console.debug('[useActivitySync] 时间线更新成功')
      } catch (error) {
        console.error('[useActivitySync] 时间线更新失败:', error)
        setSyncState((prev) => ({
          ...prev,
          pendingUpdates: Math.max(0, prev.pendingUpdates - 1)
        }))
        throw error
      }
    },
    [setTimelineData, setCurrentMaxVersion, fetchActivityCountByDate, currentMaxVersion]
  )

  // 备用策略执行
  const executeFallbackStrategy = useCallback(async () => {
    console.warn('[useActivitySync] 执行备用策略')

    // 按优先级尝试不同的策略
    const strategies = [
      { name: '部分刷新', fn: performPartialRefresh },
      { name: '全量刷新', fn: performFullRefresh },
      { name: '数据清理', fn: performDataCleanup }
    ]

    for (const strategy of strategies) {
      try {
        console.debug(`[useActivitySync] 尝试策略: ${strategy.name}`)
        const success = await strategy.fn()

        if (success) {
          console.debug(`[useActivitySync] 策略 ${strategy.name} 成功`)
          break
        }
      } catch (error) {
        console.error(`[useActivitySync] 策略 ${strategy.name} 失败:`, error)
      }
    }
  }, [performPartialRefresh, performFullRefresh, performDataCleanup])

  // 主要的事件处理函数
  const handleActivityCreated = useCallback(
    async (payload: any) => {
      if (!payload || !payload.data) {
        console.warn('[useActivitySync] 收到的活动数据格式不正确', payload)
        return
      }

      const { isAtLatest, currentMaxVersion } = stateRef.current
      const activityId = payload.data.id
      const currentSyncState = syncStateRef.current // 从 ref 获取最新的同步状态

      console.debug('[useActivitySync] 收到新活动事件', {
        activityId,
        isAtLatest,
        currentMaxVersion,
        isHealthy: currentSyncState.isHealthy,
        consecutiveFailures: currentSyncState.consecutiveFailures
      })

      try {
        // 使用带重试的增量更新函数
        const newTimelineData = await fetchIncrementalWithRetry(currentMaxVersion, 15)

        if (newTimelineData.length === 0) {
          console.debug('[useActivitySync] 没有新的活动数据')
          return
        }

        const newActivityCount = newTimelineData.reduce((sum, day) => sum + day.activities.length, 0)

        // 根据用户位置和系统健康状态决定处理策略
        if (isAtLatest) {
          console.debug('[useActivitySync] 用户在最新位置，立即更新时间线')
          await updateTimelineWithNewData(newTimelineData)
        } else {
          console.debug('[useActivitySync] 用户不在最新位置，显示通知')
          showNotification(newActivityCount, currentSyncState.consecutiveFailures > 0)
          await updateTimelineWithNewData(newTimelineData)
        }
      } catch (error) {
        console.error('[useActivitySync] 增量更新完全失败:', error)

        // 如果连续失败次数过多，启用备用策略
        // 使用 ref 中的最新状态而不是闭包中的
        if (syncStateRef.current.consecutiveFailures >= 3) {
          console.warn('[useActivitySync] 连续失败次数过多，启用备用策略')
          await executeFallbackStrategy()
        } else {
          // 显示重试通知
          showNotification(1, true)
        }
      }
    },
    // ⚠️ 关键修复：仅保留真正需要的依赖
    // syncState 通过 ref 访问，不加入依赖数组，防止处理函数频繁重新创建
    [fetchIncrementalWithRetry, updateTimelineWithNewData, showNotification, executeFallbackStrategy]
  )

  // 订阅后端的 activity-created 事件
  useActivityCreated(handleActivityCreated)

  // 后台运行，不返回状态
  // 所有同步状态监控和错误恢复都在后台自动进行
}
