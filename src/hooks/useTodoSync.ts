import { useCallback, useRef } from 'react'

import { useInsightsStore } from '@/lib/stores/insights'

import { useTodoCreated, useTodoDeleted, useTodoUpdated } from './useTauriEvents'

const DEBOUNCE_DELAY = 500 // 500ms debounce

/**
 * TODO synchronization hook
 * Listens to backend TODO events and auto-refreshes the todo list
 *
 * Strategy:
 * - Silent refresh (no toast notifications)
 * - Full refresh (no incremental updates)
 * - 500ms debounce to prevent frequent refreshes
 */
export function useTodoSync() {
  const refreshTodos = useInsightsStore((state) => state.refreshTodos)
  const todoIncludeCompleted = useInsightsStore((state) => state.todoIncludeCompleted)
  const lastRefreshTimeRef = useRef<number>(0)
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Debounced refresh function
  const debouncedRefresh = useCallback(async () => {
    const now = Date.now()

    // Clear any pending refresh
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
      refreshTimeoutRef.current = null
    }

    // Check if we should debounce
    const timeSinceLastRefresh = now - lastRefreshTimeRef.current
    if (timeSinceLastRefresh < DEBOUNCE_DELAY) {
      // Schedule a refresh after the debounce delay
      refreshTimeoutRef.current = setTimeout(() => {
        debouncedRefresh()
      }, DEBOUNCE_DELAY - timeSinceLastRefresh)
      console.debug('[useTodoSync] Debouncing refresh')
      return
    }

    lastRefreshTimeRef.current = now

    try {
      await refreshTodos(todoIncludeCompleted)
      console.debug('[useTodoSync] ✅ TODOs refreshed')
    } catch (error) {
      console.error('[useTodoSync] Failed to refresh todos:', error)
    }
  }, [refreshTodos, todoIncludeCompleted])

  // Handle TODO created event
  const handleTodoCreated = useCallback(
    (payload: any) => {
      console.debug('[useTodoSync] TODO created event received:', payload.data?.id)
      debouncedRefresh()
    },
    [debouncedRefresh]
  )

  // Handle TODO updated event
  const handleTodoUpdated = useCallback(
    (payload: any) => {
      console.debug('[useTodoSync] TODO updated event received:', payload.data?.id)
      debouncedRefresh()
    },
    [debouncedRefresh]
  )

  // Handle TODO deleted event
  const handleTodoDeleted = useCallback(
    (payload: any) => {
      console.debug('[useTodoSync] TODO deleted event received:', payload.data?.id)
      debouncedRefresh()
    },
    [debouncedRefresh]
  )

  // Subscribe to events
  useTodoCreated(handleTodoCreated)
  useTodoUpdated(handleTodoUpdated)
  useTodoDeleted(handleTodoDeleted)
}
