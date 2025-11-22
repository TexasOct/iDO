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
      setErrorMessage(message || 'Backend failed to start')
    }
  }, [])

  const ensureBackendRunning = useCallback(async () => {
    if (!inTauri) {
      markReady()
      return true
    }

    const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
    let lastMessage: string | undefined

    // Optimize the polling strategy with aggressive intervals
    // Run three fast checks (100ms), then gradually back off up to 12 attempts (~2.5s total)
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
          console.debug(`[useBackendLifecycle] Backend started on attempt ${attempt + 1}`)
          if (isLimited && coordinator?.last_error) {
            console.warn(`[useBackendLifecycle] Backend in limited mode: ${coordinator.last_error}`)
          }
          markReady()
          return true
        }

        lastMessage = coordinator?.last_error || statsResponse?.message || lastMessage
      } catch (statsError) {
        console.debug(`[useBackendLifecycle] Backend status check failed on attempt ${attempt + 1}:`, statsError)
      }

      // Wait the specified interval except for the last attempt
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
        throw new Error(response.message || 'Backend failed to start')
      }

      if (!response) {
        throw new Error('Backend start response was empty')
      }

      throw new Error('Backend service is not ready')
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      console.error('Failed to start backend system', error)
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
          throw new Error('Unable to get current Tauri window instance')
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
            // Add timeout protection: wait up to 2.5 seconds to stop the backend
            const stopPromise = stopBackend()
            const timeoutPromise = new Promise((_, reject) =>
              setTimeout(() => reject(new Error('Stopping backend timed out')), 2500)
            )
            await Promise.race([stopPromise, timeoutPromise])
          } catch (error) {
            console.warn('Failed to stop backend system:', error)
            // Do not throw; continue the shutdown logic
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

          console.debug('[useBackendLifecycle] Starting shutdown flow...')

          // Stop the backend without blocking exit
          const stopBackendWithTimeout = async () => {
            try {
              // Increase timeout to 5 seconds to give the backend time
              const stopPromise = stop()
              const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Stopping backend timed out')), 5000)
              )
              await Promise.race([stopPromise, timeoutPromise])
              console.debug('[useBackendLifecycle] Backend stopped successfully')
            } catch (error) {
              // Timeout or errors should not prevent exit
              console.warn('[useBackendLifecycle] Error while stopping backend (continuing exit):', error)
            }
          }

          // Kick off stop without waiting for completion
          void stopBackendWithTimeout()

          // Short delay to give backend a moment but do not wait long
          await new Promise((resolve) => setTimeout(resolve, 500))

          // Backend has stopped; now force quit the app
          console.debug('[useBackendLifecycle] Backend stopped, exiting app...')

          // Delay briefly to ensure backend fully stops
          await new Promise((resolve) => setTimeout(resolve, 300))

          try {
            // Fire an event so the tray can clean up
            const { emit: emitEvent } = await import('@tauri-apps/api/event')
            await emitEvent('app-will-exit')
            console.debug('[useBackendLifecycle] Emitted app-will-exit event')

            // Short delay so the tray has time to clean up
            await new Promise((resolve) => setTimeout(resolve, 100))
          } catch (emitError) {
            console.warn('[useBackendLifecycle] Failed to emit app-will-exit event', emitError)
          }

          // Try multiple exit paths to ensure termination
          let exitSuccess = false

          try {
            // Method 1: use the process plugin exit call (most reliable)
            const { exit } = await import('@tauri-apps/plugin-process')
            console.debug('[useBackendLifecycle] Calling exit(0) to force quit...')
            exit(0) // Do not await; call synchronously
            exitSuccess = true
          } catch (exitError) {
            console.error('[useBackendLifecycle] exit(0) failed, trying fallback', exitError)
          }

          // If exit(0) fails, try other methods
          if (!exitSuccess) {
            try {
              // Method 2: close and destroy the main window
              console.debug('[useBackendLifecycle] Attempting to destroy the main window...')
              await currentWindow.destroy()
            } catch (destroyError) {
              console.error('[useBackendLifecycle] Destroy failed, trying close', destroyError)
              try {
                await currentWindow.close()
              } catch (closeError) {
                console.error('[useBackendLifecycle] All exit methods failed', closeError)
              }
            }
          }
        })
      } catch (error) {
        console.error('Failed to initialize backend lifecycle logic', error)
        markError('Failed to initialize backend lifecycle logic')
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
            // Fix: add a timeout to prevent stopBackend() from hanging indefinitely
            const stopPromise = stopBackend()
            const timeoutPromise = new Promise((_, reject) =>
              setTimeout(() => reject(new Error('Stopping backend timed out')), 3000)
            )
            await Promise.race([stopPromise, timeoutPromise])
          } catch (error) {
            console.error('Failed to stop backend during unmount', error)
          }
        }
      }

      // Use a Promise rather than void, but do not await it to avoid blocking window close
      runCleanup().catch((error) => {
        console.error('Error during cleanup phase', error)
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
