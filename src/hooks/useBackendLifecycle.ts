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
    let lastMessage: string | undefined

    // 优化轮询策略：更激进的检查间隔
    // 前 3 次快速检查（100ms 间隔），然后逐步加长，最多 12 次，总时间 ~2.5s
    const checkIntervals = [50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

    for (let attempt = 0; attempt < checkIntervals.length; attempt += 1) {
      try {
        const statsResponse = await fetchBackendStats()
        const coordinator = (
          statsResponse?.data as
            | {
                coordinator?: { is_running?: boolean; status?: string; last_error?: string }
              }
            | undefined
        )?.coordinator
        const isRunning = Boolean(statsResponse?.success && coordinator?.is_running)
        const status = coordinator?.status
        const isLimited = Boolean(statsResponse?.success && status === 'requires_model')

        if (isRunning || isLimited) {
          console.debug(`[useBackendLifecycle] 后端在第 ${attempt + 1} 次检查时启动完毕`)
          if (isLimited && coordinator?.last_error) {
            console.warn(`[useBackendLifecycle] 后端处于受限模式: ${coordinator.last_error}`)
          }
          markReady()
          return true
        }

        lastMessage = coordinator?.last_error || statsResponse?.message || lastMessage
      } catch (statsError) {
        console.debug(`[useBackendLifecycle] 第 ${attempt + 1} 次检查后台状态失败:`, statsError)
      }

      // 除了最后一次外，等待指定的间隔时间
      if (attempt < checkIntervals.length - 1) {
        await wait(checkIntervals[attempt])
      }
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

        // Listen for the custom 'app-exit' event instead of onCloseRequested
        // The tray hook will handle window close to hide instead of exit
        const { listen: listenToEvent } = await import('@tauri-apps/api/event')
        removeCloseListener = await listenToEvent('app-exit', async () => {
          if (removeCloseListener) {
            removeCloseListener()
            removeCloseListener = undefined
          }

          console.debug('[useBackendLifecycle] 开始关闭流程...')

          // 停止后端，但不让它阻止退出
          const stopBackendWithTimeout = async () => {
            try {
              // 增加超时到 5 秒，给后端充足时间
              const stopPromise = stop()
              const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('停止后端超时')), 5000)
              )
              await Promise.race([stopPromise, timeoutPromise])
              console.debug('[useBackendLifecycle] 后端成功停止')
            } catch (error) {
              // 超时或错误不应阻止退出
              console.warn('[useBackendLifecycle] 停止后端时出错（继续退出）:', error)
            }
          }

          // 启动停止但不等待完成
          void stopBackendWithTimeout()

          // 短暂延迟给后端一点时间，但不等太久
          await new Promise((resolve) => setTimeout(resolve, 500))

          // 后端已停止，现在强制退出应用
          console.debug('[useBackendLifecycle] 后端已停止，正在退出应用...')

          // 延迟一下确保后端完全停止
          await new Promise((resolve) => setTimeout(resolve, 300))

          try {
            // 先发射事件通知托盘清理
            const { emit: emitEvent } = await import('@tauri-apps/api/event')
            await emitEvent('app-will-exit')
            console.debug('[useBackendLifecycle] 已发送 app-will-exit 事件')

            // 短暂延迟让托盘有时间清理
            await new Promise((resolve) => setTimeout(resolve, 100))
          } catch (emitError) {
            console.warn('[useBackendLifecycle] 发送 app-will-exit 事件失败', emitError)
          }

          // 尝试多种退出方法以确保应用真正退出
          let exitSuccess = false

          try {
            // 方法1: 使用 process 插件 exit - 这应该是最可靠的
            const { exit } = await import('@tauri-apps/plugin-process')
            console.debug('[useBackendLifecycle] 调用 exit(0) 强制退出...')
            exit(0) // 注意：不要 await，直接同步调用
            exitSuccess = true
          } catch (exitError) {
            console.error('[useBackendLifecycle] exit(0) 失败，尝试备用方案', exitError)
          }

          // 如果 exit(0) 失败，尝试其他方法
          if (!exitSuccess) {
            try {
              // 方法2: 关闭并销毁主窗口
              console.debug('[useBackendLifecycle] 尝试 destroy 主窗口...')
              await currentWindow.destroy()
            } catch (destroyError) {
              console.error('[useBackendLifecycle] destroy 失败，尝试 close', destroyError)
              try {
                await currentWindow.close()
              } catch (closeError) {
                console.error('[useBackendLifecycle] 所有退出方法都失败了', closeError)
              }
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
