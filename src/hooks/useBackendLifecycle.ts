import type { CloseRequestedEvent } from '@tauri-apps/api/window'
import { useCallback, useEffect, useRef, useState } from 'react'

import { fetchBackendStats, startBackend, stopBackend } from '@/lib/services/system'
import { isTauri } from '@/lib/utils/tauri'

export type BackendStatus = 'starting' | 'ready' | 'error'

interface BackendLifecycleState {
  status: BackendStatus
  errorMessage: string | null
  retry: () => Promise<void>
  isTauriApp: boolean
}

export function useBackendLifecycle(): BackendLifecycleState {
  const inTauri = isTauri()
  const [status, setStatus] = useState<BackendStatus>(inTauri ? 'starting' : 'ready')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const backendReadyRef = useRef(!inTauri)
  const startInFlightRef = useRef(false)
  const isMountedRef = useRef(true)

  useEffect(() => {
    return () => {
      isMountedRef.current = false
    }
  }, [])

  const markReady = useCallback(() => {
    backendReadyRef.current = true
    if (isMountedRef.current) {
      setStatus('ready')
      setErrorMessage(null)
    }
  }, [])

  const markError = useCallback((message?: string) => {
    backendReadyRef.current = false
    if (isMountedRef.current) {
      setStatus('error')
      setErrorMessage(message || '后台启动失败')
    }
  }, [])

  const ensureBackendRunning = useCallback(async () => {
    if (!inTauri) {
      markReady()
      return true
    }

    const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
    const maxChecks = 4
    let lastMessage: string | undefined

    for (let attempt = 0; attempt < maxChecks; attempt += 1) {
      try {
        const statsResponse = await fetchBackendStats()
        const coordinator = (statsResponse?.data as { coordinator?: { is_running?: boolean } } | undefined)?.coordinator
        const isRunning = Boolean(statsResponse?.success && coordinator?.is_running)

        if (isRunning) {
          markReady()
          return true
        }

        lastMessage = statsResponse?.message || lastMessage
      } catch (statsError) {
        console.error('检查后台状态失败', statsError)
      }

      await wait(400 * (attempt + 1))
    }

    if (lastMessage) {
      markError(lastMessage)
    }

    return false
  }, [inTauri, markError, markReady])

  const startBackendProcess = useCallback(async () => {
    if (!inTauri) {
      markReady()
      return
    }

    if (backendReadyRef.current || startInFlightRef.current) {
      return
    }

    startInFlightRef.current = true

    if (isMountedRef.current) {
      setStatus('starting')
      setErrorMessage(null)
    }

    try {
      const response = await startBackend()
      const confirmed = await ensureBackendRunning()
      if (confirmed) {
        return
      }

      if (response && !response.success) {
        throw new Error(response.message || '后台启动失败')
      }

      if (!response) {
        throw new Error('后台启动返回为空')
      }

      throw new Error('后台服务未就绪')
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      console.error('启动后端系统失败', error)
      markError(message)
    } finally {
      startInFlightRef.current = false
    }
  }, [ensureBackendRunning, inTauri, markError, markReady])

  useEffect(() => {
    if (!inTauri) {
      return
    }

    let removeReadyListener: (() => void) | undefined
    let removeCloseListener: (() => void) | undefined
    let backendStopped = false

    const setup = async () => {
      try {
        const [{ listen }, windowModule] = await Promise.all([
          import('@tauri-apps/api/event'),
          import('@tauri-apps/api/window')
        ])

        const currentWindow = windowModule.getCurrentWindow()

        if (!currentWindow) {
          throw new Error('无法获取当前 Tauri 窗口实例')
        }

        const start = async () => {
          await startBackendProcess()
        }

        const stop = async () => {
          if (backendStopped) {
            return
          }

          backendStopped = true
          backendReadyRef.current = false
          try {
            // 添加超时保护：最多等待 2.5 秒停止后端
            const stopPromise = stopBackend()
            const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('停止后端超时')), 2500))
            await Promise.race([stopPromise, timeoutPromise])
          } catch (error) {
            console.warn('停止后端系统失败:', error)
            // 不抛出错误，继续执行关闭逻辑
          }
        }

        removeReadyListener = await listen('tauri://ready', async () => {
          await start()
          if (removeReadyListener) {
            removeReadyListener()
            removeReadyListener = undefined
          }
        })

        await start()

        removeCloseListener = await currentWindow.onCloseRequested(async (event: CloseRequestedEvent) => {
          event.preventDefault()

          if (removeCloseListener) {
            removeCloseListener()
            removeCloseListener = undefined
          }

          try {
            // 添加超时机制：最多等待 3 秒停止后端
            const stopPromise = stop()
            const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('停止后端超时')), 3000))
            await Promise.race([stopPromise, timeoutPromise]).catch((error) => {
              console.warn('[useBackendLifecycle] 停止后端时出错:', error)
              // 即使出错也继续关闭窗口
            })
          } finally {
            // 无论如何都关闭窗口
            try {
              await currentWindow.close()
            } catch (closeError) {
              console.error('[useBackendLifecycle] 关闭窗口失败:', closeError)
            }
          }
        })
      } catch (error) {
        console.error('初始化后端生命周期逻辑失败', error)
        markError('初始化后端生命周期逻辑失败')
      }
    }

    void setup()

    return () => {
      const runCleanup = async () => {
        if (removeReadyListener) {
          removeReadyListener()
        }

        if (removeCloseListener) {
          removeCloseListener()
        }

        if (!backendStopped) {
          backendStopped = true
          backendReadyRef.current = false
          try {
            // 修复：添加超时机制，防止 stopBackend() 无限期地卡住
            const stopPromise = stopBackend()
            const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('停止后端超时')), 3000))
            await Promise.race([stopPromise, timeoutPromise])
          } catch (error) {
            console.error('组件卸载时停止后端失败', error)
          }
        }
      }

      // 使用 Promise 而不是 void，但不等待完成以避免阻塞窗口关闭
      runCleanup().catch((error) => {
        console.error('清理阶段出错', error)
      })
    }
  }, [inTauri, markError, startBackendProcess])

  return {
    status,
    errorMessage,
    retry: startBackendProcess,
    isTauriApp: inTauri
  }
}
