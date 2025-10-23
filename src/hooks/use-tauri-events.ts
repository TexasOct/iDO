import { useEffect, useRef } from 'react'

import { isTauri } from '@/lib/utils/tauri'

/**
 * 监听 Tauri 事件的 Hook
 * 使用 useRef 存储处理函数，避免因处理函数变化而重新注册事件监听器
 * 事件监听器只在组件挂载/卸载时注册/注销，处理函数通过 ref 保持最新
 *
 * @param eventName 事件名称
 * @param handler 事件处理函数
 */
export function useTauriEvent<T = any>(eventName: string, handler: (payload: T) => void) {
  // 使用 ref 存储最新的处理函数
  const handlerRef = useRef<(payload: T) => void>(handler)

  // 在处理函数改变时更新 ref（不触发事件监听器重新注册）
  useEffect(() => {
    handlerRef.current = handler
  }, [handler])

  // 事件监听器的注册/注销，只依赖于 eventName
  useEffect(() => {
    // 如果不在 Tauri 环境中，不执行任何操作
    if (!isTauri()) {
      return
    }

    let unlisten: (() => void) | undefined

    // 动态导入 Tauri API
    import('@tauri-apps/api/event')
      .then(({ listen }) => {
        return listen<T>(eventName, (event) => {
          // 调用 ref 中最新的处理函数
          handlerRef.current(event.payload)
        })
      })
      .then((fn) => {
        unlisten = fn
      })
      .catch((error) => {
        console.error(`Failed to listen to event ${eventName}:`, error)
      })

    // 清理函数
    return () => {
      if (unlisten) {
        unlisten()
      }
    }
  }, [eventName])
}

/**
 * Agent 任务更新事件 Hook
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
 * 活动更新事件 Hook（当活动被更新或删除时触发）
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
 * 活动创建事件 Hook（后端持久化活动时触发）
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
 * 活动删除事件 Hook
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
 * 批量更新完成事件 Hook（多个活动批量更新时触发）
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
