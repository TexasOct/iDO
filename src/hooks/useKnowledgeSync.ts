import { useCallback, useRef } from 'react'

import { useInsightsStore } from '@/lib/stores/insights'

import { useKnowledgeCreated, useKnowledgeDeleted, useKnowledgeUpdated } from './useTauriEvents'

const DEBOUNCE_DELAY = 500 // 500ms debounce

/**
 * Knowledge synchronization hook
 * Listens to backend knowledge events and auto-refreshes the knowledge list
 *
 * Strategy:
 * - Silent refresh (no toast notifications)
 * - Full refresh (no incremental updates)
 * - 500ms debounce to prevent frequent refreshes
 */
export function useKnowledgeSync() {
  const refreshKnowledge = useInsightsStore((state) => state.refreshKnowledge)
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
      console.debug('[useKnowledgeSync] Debouncing refresh')
      return
    }

    lastRefreshTimeRef.current = now

    try {
      await refreshKnowledge()
      console.debug('[useKnowledgeSync] ✅ Knowledge refreshed')
    } catch (error) {
      console.error('[useKnowledgeSync] Failed to refresh knowledge:', error)
    }
  }, [refreshKnowledge])

  // Handle knowledge created event
  const handleKnowledgeCreated = useCallback(
    (payload: any) => {
      console.debug('[useKnowledgeSync] Knowledge created event received:', payload.data?.id)
      debouncedRefresh()
    },
    [debouncedRefresh]
  )

  // Handle knowledge updated event
  const handleKnowledgeUpdated = useCallback(
    (payload: any) => {
      console.debug('[useKnowledgeSync] Knowledge updated event received:', payload.data?.id)
      debouncedRefresh()
    },
    [debouncedRefresh]
  )

  // Handle knowledge deleted event
  const handleKnowledgeDeleted = useCallback(
    (payload: any) => {
      console.debug('[useKnowledgeSync] Knowledge deleted event received:', payload.data?.id)
      debouncedRefresh()
    },
    [debouncedRefresh]
  )

  // Subscribe to events
  useKnowledgeCreated(handleKnowledgeCreated)
  useKnowledgeUpdated(handleKnowledgeUpdated)
  useKnowledgeDeleted(handleKnowledgeDeleted)
}
