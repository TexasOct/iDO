import { useEffect, useRef } from 'react'

import { isTauri } from '@/lib/utils/tauri'

/**
 * Hook for listening to Tauri events
 * Stores handlers in refs so changing callbacks does not re-register listeners
 * Registers/unregisters listeners on mount/unmount; refs keep handlers fresh
 *
 * @param eventName Event name
 * @param handler Event handler
 */
export function useTauriEvent<T = any>(eventName: string, handler: (payload: T) => void) {
  // Store the latest handler in a ref
  const handlerRef = useRef<(payload: T) => void>(handler)

  // Update the ref when the handler changes without re-registering listeners
  useEffect(() => {
    handlerRef.current = handler
  }, [handler])

  // Register/unregister listeners only when the event name changes
  useEffect(() => {
    // No-op when not running inside Tauri
    if (!isTauri()) {
      console.debug(`[useTauriEvent] Not running in Tauri, skipping event listener: ${eventName}`)
      return
    }

    let unlisten: (() => void) | undefined

    // Dynamically import the Tauri API
    import('@tauri-apps/api/event')
      .then(({ listen }) => {
        console.debug(`[useTauriEvent] Listening to event: ${eventName}`)
        return listen<T>(eventName, (event) => {
          console.debug(`[useTauriEvent] Received event: ${eventName}`, event.payload)
          // Invoke the latest handler from the ref
          handlerRef.current(event.payload)
        })
      })
      .then((fn) => {
        unlisten = fn
        console.debug(`[useTauriEvent] ✅ Event listener registered: ${eventName}`)
      })
      .catch((error) => {
        console.error(`[useTauriEvent] ❌ Failed to listen to event ${eventName}:`, error)
      })

    // Cleanup function
    return () => {
      if (unlisten) {
        console.debug(`[useTauriEvent] Unlistened event: ${eventName}`)
        unlisten()
      }
    }
  }, [eventName])
}

/**
 * Agent task update hook
 */
export interface TaskUpdatePayload {
  taskId: string
  status: 'todo' | 'processing' | 'done' | 'failed'
  progress?: number
  result?: any
  error?: string
}

export function useTaskUpdates(onUpdate: (payload: TaskUpdatePayload) => void) {
  useTauriEvent('agent-task-update', onUpdate)
}

/**
 * Activity update hook (fires when activities update or delete)
 */
export interface ActivityUpdatedPayload {
  type: string
  data: {
    id: string
    description: string
    startTime: string
    endTime: string
    sourceEvents: any[]
    version: number
    createdAt: string
  }
  timestamp: string
}

export function useActivityUpdated(onUpdated: (payload: ActivityUpdatedPayload) => void) {
  useTauriEvent<ActivityUpdatedPayload>('activity-updated', onUpdated)
}

/**
 * Activity creation hook (fires when backend persists activities)
 */
export interface ActivityCreatedPayload {
  type: string
  data: {
    id: string
    description: string
    startTime: string
    endTime: string
    sourceEvents: any[]
    version: number
    createdAt: string
  }
  timestamp: string
}

export function useActivityCreated(onCreated: (payload: ActivityCreatedPayload) => void) {
  useTauriEvent<ActivityCreatedPayload>('activity-created', onCreated)
}

/**
 * Activity deletion hook
 */
export interface ActivityDeletedPayload {
  type: string
  data: {
    id: string
    deletedAt: string
  }
  timestamp: string
}

export function useActivityDeleted(onDeleted: (payload: ActivityDeletedPayload) => void) {
  useTauriEvent<ActivityDeletedPayload>('activity-deleted', onDeleted)
}

/**
 * Bulk update completion hook (fires for batched updates)
 */
export interface BulkUpdateCompletedPayload {
  type: string
  data: {
    updatedCount: number
    timestamp: string
  }
  timestamp: string
}

export function useBulkUpdateCompleted(onCompleted: (payload: BulkUpdateCompletedPayload) => void) {
  useTauriEvent<BulkUpdateCompletedPayload>('bulk-update-completed', onCompleted)
}

/**
 * Activity merged hook (fires when activities are merged)
 */
export interface ActivityMergedPayload {
  type: string
  data: {
    mergedActivityId: string
    originalActivityIds: string[]
    timestamp: string
  }
  timestamp: string
}

export function useActivityMerged(onMerged: (payload: ActivityMergedPayload) => void) {
  useTauriEvent<ActivityMergedPayload>('activity-merged', onMerged)
}

/**
 * Activity split hook (fires when an activity is split)
 */
export interface ActivitySplitPayload {
  type: string
  data: {
    originalActivityId: string
    newActivityIds: string[]
    timestamp: string
  }
  timestamp: string
}

export function useActivitySplit(onSplit: (payload: ActivitySplitPayload) => void) {
  useTauriEvent<ActivitySplitPayload>('activity-split', onSplit)
}
