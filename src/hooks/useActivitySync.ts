import { useCallback, useEffect, useRef, useState } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { useActivityCreated } from './useTauriEvents'
import { fetchActivitiesIncremental } from '@/lib/services/activity'

const MAX_TIMELINE_ITEMS = 100
const MAX_RETRY_ATTEMPTS = 3
const RETRY_DELAYS = [1000, 2000, 4000] // Exponential backoff
const HEALTH_CHECK_INTERVAL = 30000 // 30-second health check
const SYNC_TIMEOUT = 10000 // 10-second sync timeout

interface SyncState {
  isHealthy: boolean
  lastSyncTime: number
  consecutiveFailures: number
  pendingUpdates: number
}

/**
 * Activity synchronization hook
 * Includes incremental updates, error recovery, and fallback strategies
 */
export function useActivitySync() {
  // Base state
  const isAtLatest = useActivityStore((state) => state.isAtLatest)
  const currentMaxVersion = useActivityStore((state) => state.currentMaxVersion)
  const setTimelineData = useActivityStore((state) => state.setTimelineData)
  const setCurrentMaxVersion = useActivityStore((state) => state.setCurrentMaxVersion)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)
  const fetchTimelineData = useActivityStore((state) => state.fetchTimelineData)

  // Sync state
  const [syncState, setSyncState] = useState<SyncState>({
    isHealthy: true,
    lastSyncTime: Date.now(),
    consecutiveFailures: 0,
    pendingUpdates: 0
  })

  // Store state in refs to avoid incessant dependency changes
  const stateRef = useRef({ isAtLatest, currentMaxVersion })
  const syncStateRef = useRef<SyncState>(syncState) // Track syncState in a ref so handlers always read the latest value
  const retryTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map())
  const healthCheckIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Keep the ref copy in sync
  useEffect(() => {
    stateRef.current = { isAtLatest, currentMaxVersion }
  }, [isAtLatest, currentMaxVersion])

  // Sync the syncState ref
  useEffect(() => {
    syncStateRef.current = syncState
  }, [syncState])

  // Health check mechanism
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

        console.debug('[useActivitySync] Health check passed')
      } catch (error) {
        console.warn('[useActivitySync] Health check failed:', error)

        setSyncState((prev) => ({
          ...prev,
          isHealthy: false,
          consecutiveFailures: prev.consecutiveFailures + 1
        }))
      }
    }

    // Start the health check
    healthCheckIntervalRef.current = setInterval(performHealthCheck, HEALTH_CHECK_INTERVAL)

    // Run an immediate health check
    performHealthCheck()

    return () => {
      if (healthCheckIntervalRef.current) {
        clearInterval(healthCheckIntervalRef.current)
      }
    }
  }, [currentMaxVersion])

  // Clear retry timers
  useEffect(() => {
    return () => {
      retryTimeoutsRef.current.forEach((timeout) => clearTimeout(timeout))
      retryTimeoutsRef.current.clear()
    }
  }, [])

  // Incremental update function with retries
  const fetchIncrementalWithRetry = useCallback(
    async (version: number, limit: number, attempt: number = 0): Promise<any[]> => {
      const operationId = `fetch-${version}-${Date.now()}`

      try {
        console.debug(`[useActivitySync] Attempt incremental update (${attempt + 1}/${MAX_RETRY_ATTEMPTS})`)

        // Configure a timeout
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error('Sync timeout')), SYNC_TIMEOUT)
        })

        const dataPromise = fetchActivitiesIncremental(version, limit)
        const result = await Promise.race([dataPromise, timeoutPromise])

        // Clear retry timers on success
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
        console.error(`[useActivitySync] Incremental update failed (attempt ${attempt + 1}):`, error)

        if (attempt < MAX_RETRY_ATTEMPTS - 1) {
          const delay = RETRY_DELAYS[attempt] || RETRY_DELAYS[RETRY_DELAYS.length - 1]
          console.debug(`[useActivitySync] Retrying in ${delay}ms`)

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
          // All retries failed
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

  // Fallback: full refresh
  const performFullRefresh = useCallback(async () => {
    console.warn('[useActivitySync] Enabling fallback: full refresh')

    try {
      // Reset versions to force fetching the latest data
      setCurrentMaxVersion(0)

      // Perform the full refresh
      await fetchTimelineData({ limit: 50 })

      console.debug('[useActivitySync] Full refresh succeeded')
      return true
    } catch (error) {
      console.error('[useActivitySync] Full refresh failed:', error)
      return false
    }
  }, [fetchTimelineData, setCurrentMaxVersion])

  // Partial refresh strategy
  const performPartialRefresh = useCallback(async () => {
    console.warn('[useActivitySync] Enabling fallback: partial refresh')

    try {
      await fetchTimelineData({ limit: 20 })
      console.debug('[useActivitySync] Partial refresh succeeded')
      return true
    } catch (error) {
      console.error('[useActivitySync] Partial refresh failed:', error)
      return false
    }
  }, [fetchTimelineData])

  // Data cleanup strategy
  const performDataCleanup = useCallback(async () => {
    console.warn('[useActivitySync] Enabling fallback: data cleanup')

    try {
      // Clear the timeline data and start over
      setTimelineData(() => [])
      setCurrentMaxVersion(0)

      // Reload the data
      await fetchTimelineData({ limit: 15 })

      console.debug('[useActivitySync] Data cleanup finished')
      return true
    } catch (error) {
      console.error('[useActivitySync] Data cleanup failed:', error)
      return false
    }
  }, [setTimelineData, setCurrentMaxVersion, fetchTimelineData])

  // Smart notification system
  const showNotification = useCallback((activityCount: number, isRetry: boolean = false) => {
    const notification = document.createElement('div')
    const notificationClass = isRetry
      ? 'fixed top-4 right-4 z-50 transform rounded-lg bg-destructive text-destructive-foreground px-4 py-3 shadow-lg transition-all duration-300 translate-x-full'
      : 'fixed top-4 right-4 z-50 transform rounded-lg bg-primary text-primary-foreground px-4 py-3 shadow-lg transition-all duration-300 translate-x-full'

    notification.className = notificationClass
    notification.innerHTML = `
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-5 5-5-5h5v-5a7.5 7.5 0 1 0-15 0v5h5l-5 5-5-5h5v-5a7.5 7.5 0 1 1 15 0v5z"></path>
          </svg>
          <div class="h-2 w-2 animate-pulse rounded-full" style="background-color: currentColor; opacity: 0.7"></div>
        </div>
        <div class="flex-1">
          <p class="text-sm font-medium">${isRetry ? 'Retrying sync' : 'New activities'}</p>
          <p class="text-xs opacity-90">${activityCount} new activities ${isRetry ? 'are retrying sync' : 'added'}</p>
        </div>
        <div class="flex items-center gap-1">
          <button class="rounded px-2 py-1 text-xs transition-colors" style="background-color: currentColor; opacity: 0.2" onmouseover="this.style.opacity='0.3'" onmouseout="this.style.opacity='0.2'" onclick="this.parentElement.parentElement.parentElement.remove()">View</button>
          <button class="p-1 transition-colors" style="opacity: 0.7" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'" onclick="this.parentElement.parentElement.parentElement.remove()">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>
    `

    document.body.appendChild(notification)

    // Show animation
    setTimeout(() => {
      notification.classList.remove('translate-x-full')
    }, 100)

    // Auto hide
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

  // Function to update the timeline
  const updateTimelineWithNewData = useCallback(
    async (newTimelineData: any[]) => {
      try {
        setSyncState((prev) => ({ ...prev, pendingUpdates: prev.pendingUpdates + 1 }))

        // Efficiently merge new data at the top of the timeline
        setTimelineData((prevData) => {
          const dateMap = new Map<string, any>()

          // Add existing data first
          prevData.forEach((day) => {
            dateMap.set(day.date, { ...day })
          })

          // Then merge new data
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

          // Convert to an array and sort
          let merged = Array.from(dateMap.values()).sort((a, b) => (a.date > b.date ? -1 : 1))

          // Sliding window
          if (merged.length > MAX_TIMELINE_ITEMS) {
            const removedCount = merged.length - MAX_TIMELINE_ITEMS
            console.debug(`[useActivitySync] Sliding window removed ${removedCount} old day blocks`)
            merged = merged.slice(0, MAX_TIMELINE_ITEMS)
          }

          return merged
        })

        // Update the version number
        const maxVersion = newTimelineData.reduce(
          (max, day) => Math.max(max, ...day.activities.map((a: any) => a.version || 0)),
          currentMaxVersion
        )
        setCurrentMaxVersion(maxVersion)

        // Update date counts asynchronously
        fetchActivityCountByDate()

        setSyncState((prev) => ({
          ...prev,
          pendingUpdates: Math.max(0, prev.pendingUpdates - 1),
          lastSyncTime: Date.now()
        }))

        console.debug('[useActivitySync] Timeline update succeeded')
      } catch (error) {
        console.error('[useActivitySync] Timeline update failed:', error)
        setSyncState((prev) => ({
          ...prev,
          pendingUpdates: Math.max(0, prev.pendingUpdates - 1)
        }))
        throw error
      }
    },
    [setTimelineData, setCurrentMaxVersion, fetchActivityCountByDate, currentMaxVersion]
  )

  // Execute fallback strategies
  const executeFallbackStrategy = useCallback(async () => {
    console.warn('[useActivitySync] Executing fallback strategies')

    // Try fallback strategies by priority
    const strategies = [
      { name: 'Partial refresh', fn: performPartialRefresh },
      { name: 'Full refresh', fn: performFullRefresh },
      { name: 'Data cleanup', fn: performDataCleanup }
    ]

    for (const strategy of strategies) {
      try {
        console.debug(`[useActivitySync] Trying strategy: ${strategy.name}`)
        const success = await strategy.fn()

        if (success) {
          console.debug(`[useActivitySync] Strategy ${strategy.name} succeeded`)
          break
        }
      } catch (error) {
        console.error(`[useActivitySync] Strategy ${strategy.name} failed:`, error)
      }
    }
  }, [performPartialRefresh, performFullRefresh, performDataCleanup])

  // Primary event handler
  const handleActivityCreated = useCallback(
    async (payload: any) => {
      if (!payload || !payload.data) {
        console.warn('[useActivitySync] Activity payload has invalid format', payload)
        return
      }

      const { isAtLatest, currentMaxVersion } = stateRef.current
      const activityId = payload.data.id
      const currentSyncState = syncStateRef.current // Read the latest sync state from the ref

      console.debug('[useActivitySync] Received activity event', {
        activityId,
        isAtLatest,
        currentMaxVersion,
        isHealthy: currentSyncState.isHealthy,
        consecutiveFailures: currentSyncState.consecutiveFailures
      })

      try {
        // Use the retry-enabled incremental updater
        const newTimelineData = await fetchIncrementalWithRetry(currentMaxVersion, 15)

        if (newTimelineData.length === 0) {
          console.debug('[useActivitySync] No new activity data')
          return
        }

        const newActivityCount = newTimelineData.reduce((sum, day) => sum + day.activities.length, 0)

        // Decide the handling strategy based on user position and system health
        if (isAtLatest) {
          console.debug('[useActivitySync] User is at the latest position, updating timeline now')
          await updateTimelineWithNewData(newTimelineData)
        } else {
          console.debug('[useActivitySync] User is not at the latest position, showing notification')
          showNotification(newActivityCount, currentSyncState.consecutiveFailures > 0)
          await updateTimelineWithNewData(newTimelineData)
        }
      } catch (error) {
        console.error('[useActivitySync] Incremental update completely failed:', error)

        // Enable fallback when we exceed the failure threshold
        // Use the ref state rather than the stale closure state
        if (syncStateRef.current.consecutiveFailures >= 3) {
          console.warn('[useActivitySync] Too many consecutive failures, enabling fallback')
          await executeFallbackStrategy()
        } else {
          // Show the retry notification
          showNotification(1, true)
        }
      }
    },
    // ⚠️ Critical fix: only keep truly necessary dependencies
    // Access syncState via ref so the handler is not recreated unnecessarily
    [fetchIncrementalWithRetry, updateTimelineWithNewData, showNotification, executeFallbackStrategy]
  )

  // Subscribe to backend activity-created events
  useActivityCreated(handleActivityCreated)

  // Runs in the background, returns no state
  // All sync monitoring and recovery happens automatically in the background
}
