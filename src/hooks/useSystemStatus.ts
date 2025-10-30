import { useEffect, useRef, useState } from 'react'

import { fetchBackendStats } from '@/lib/services/system'
import { isTauri } from '@/lib/utils/tauri'

export type SystemHealthStatus = 'running' | 'limited' | 'stopped' | 'error' | 'unknown'

interface SystemStatusState {
  status: SystemHealthStatus
  message: string | null
  loading: boolean
  activeModel: {
    name?: string
    lastTestStatus?: boolean
    lastTestedAt?: string | null
    lastTestError?: string | null
  } | null
}

export function useSystemStatus(pollInterval = 5000): SystemStatusState {
  const inTauri = isTauri()
  const [status, setStatus] = useState<SystemHealthStatus>(inTauri ? 'unknown' : 'running')
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(inTauri)
  const [activeModel, setActiveModel] = useState<SystemStatusState['activeModel']>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!inTauri) {
      setLoading(false)
      return
    }

    let cancelled = false

    const scheduleNext = () => {
      if (cancelled) {
        return
      }
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
      timerRef.current = setTimeout(fetchStatus, pollInterval)
    }

    const fetchStatus = async () => {
      try {
        const response = await fetchBackendStats()
        const coordinator = (
          response?.data as
            | {
                coordinator?: {
                  is_running?: boolean
                  status?: string
                  last_error?: string
                  active_model?: {
                    name?: string
                    last_test_status?: boolean
                    lastTestStatus?: boolean
                    last_tested_at?: string | null
                    lastTestedAt?: string | null
                    last_test_error?: string | null
                    lastTestError?: string | null
                  }
                }
              }
            | undefined
        )?.coordinator

        if (cancelled) {
          return
        }

        setLoading(false)

        const activeModelData = coordinator?.active_model
        const sanitizedActiveModel = activeModelData
          ? {
              name: activeModelData.name,
              lastTestStatus: Boolean(activeModelData.lastTestStatus ?? activeModelData.last_test_status ?? false),
              lastTestedAt: activeModelData.lastTestedAt ?? activeModelData.last_tested_at ?? null,
              lastTestError: activeModelData.lastTestError ?? activeModelData.last_test_error ?? null
            }
          : null
        setActiveModel(sanitizedActiveModel)

        const isRunning = Boolean(response?.success && coordinator?.is_running)
        const testPassed = Boolean(sanitizedActiveModel?.lastTestStatus)

        if (isRunning && testPassed) {
          setStatus('running')
          setMessage(null)
          scheduleNext()
          return
        }

        const coordinatorStatus = coordinator?.status
        const coordinatorMessage = coordinator?.last_error || response?.message || null

        if (isRunning && !testPassed) {
          setStatus('limited')
          setMessage(sanitizedActiveModel?.lastTestError || coordinatorMessage)
          scheduleNext()
          return
        }

        if (response?.success && coordinatorStatus === 'requires_model') {
          setStatus('limited')
          setMessage(coordinatorMessage)
          scheduleNext()
          return
        }

        if (response?.success) {
          setStatus('stopped')
          setMessage(coordinatorMessage)
        } else {
          setStatus('error')
          setMessage(coordinatorMessage || 'Failed to fetch backend status')
        }

        scheduleNext()
      } catch (error) {
        if (cancelled) {
          return
        }

        console.debug('[useSystemStatus] 获取系统状态失败:', error)
        setLoading(false)
        setStatus('error')
        setMessage(error instanceof Error ? error.message : String(error))
        scheduleNext()
      }
    }

    fetchStatus()

    return () => {
      cancelled = true
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [inTauri, pollInterval])

  return { status, message, loading, activeModel }
}
