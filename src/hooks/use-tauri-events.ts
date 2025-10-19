import { useEffect } from 'react'

/**
 * 检查是否在 Tauri 环境中运行
 */
function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window
}

/**
 * 监听 Tauri 事件的 Hook
 * @param eventName 事件名称
 * @param handler 事件处理函数
 */
export function useTauriEvent<T = any>(eventName: string, handler: (payload: T) => void) {
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
          handler(event.payload)
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
  }, [eventName, handler])
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
 * 活动记录更新事件 Hook
 */
export interface ActivityUpdatePayload {
  type: 'new_activity' | 'update_activity'
  activityId: string
  data: any
}

export function useActivityUpdates(onUpdate: (payload: ActivityUpdatePayload) => void) {
  useTauriEvent('activity-update', onUpdate)
}
