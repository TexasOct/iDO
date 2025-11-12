import { useCallback, useEffect, useRef } from 'react'

import { isTauri } from '@/lib/utils/tauri'
import type { MonitorInfo, ScreenSetting } from '@/lib/types/settings'
import { getScreenSettings, startMonitorsAutoRefresh, updateScreenSettings } from '@/lib/client/screens'
import { useTauriEvent } from './useTauriEvents'
import { toast } from 'sonner'

interface MonitorsChangedPayload {
  type: 'monitors_changed'
  data?: {
    monitors?: MonitorInfo[]
    count?: number
  }
  timestamp?: string
}

function buildSettingsFromMonitors(monitors: MonitorInfo[], existing: ScreenSetting[]): ScreenSetting[] {
  const existingMap = new Map<number, ScreenSetting>()
  existing.forEach((item) => {
    const idx = Number(item.monitor_index)
    if (!Number.isNaN(idx)) {
      existingMap.set(idx, item)
    }
  })

  return monitors.map((monitor) => {
    const prev = existingMap.get(monitor.index)
    return {
      monitor_index: monitor.index,
      monitor_name: monitor.name,
      is_enabled: prev ? prev.is_enabled : monitor.is_primary,
      resolution: monitor.resolution,
      is_primary: monitor.is_primary
    }
  })
}

function signatureForSettings(settings: ScreenSetting[]): string {
  return JSON.stringify(
    settings
      .map((s) => ({
        index: s.monitor_index,
        enabled: s.is_enabled,
        resolution: s.resolution,
        primary: s.is_primary
      }))
      .sort((a, b) => a.index - b.index)
  )
}

export function useMonitorAutoSync(intervalSeconds: number = 10) {
  const isProcessingRef = useRef(false)
  const lastSignatureRef = useRef<string | null>(null)
  const isInitializedRef = useRef(false)

  const handleMonitorsChanged = useCallback(async (payload: MonitorsChangedPayload) => {
    const monitors = payload?.data?.monitors
    if (!Array.isArray(monitors) || monitors.length === 0) {
      return
    }

    // Skip the very first event to avoid spurious changes at startup
    if (!isInitializedRef.current) {
      isInitializedRef.current = true
      try {
        const settingsResponse: any = await getScreenSettings()
        const existingScreens = (settingsResponse?.data?.screens ?? []) as ScreenSetting[]
        const nextSettings = buildSettingsFromMonitors(monitors, existingScreens)
        lastSignatureRef.current = signatureForSettings(nextSettings)
      } catch (error) {
        console.error('[useMonitorAutoSync] Failed to initialize on first event', error)
      }
      return
    }

    if (isProcessingRef.current) {
      return
    }

    isProcessingRef.current = true
    try {
      const settingsResponse: any = await getScreenSettings()
      const existingScreens = (settingsResponse?.data?.screens ?? []) as ScreenSetting[]

      const nextSettings = buildSettingsFromMonitors(monitors, existingScreens)
      const nextSignature = signatureForSettings(nextSettings)

      if (nextSignature === lastSignatureRef.current) {
        return
      }

      const response: any = await updateScreenSettings({ screens: nextSettings as any[] })
      if (response?.success) {
        lastSignatureRef.current = nextSignature
        toast.success('检测到显示器变更，已自动更新截屏设置')
      } else if (response?.error) {
        toast.error(`自动更新显示器设置失败: ${response.error}`)
      }
    } catch (error) {
      console.error('[useMonitorAutoSync] 自动更新显示器设置失败', error)
      toast.error('自动更新显示器设置失败')
    } finally {
      isProcessingRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!isTauri()) {
      return
    }

    let cancelled = false
    ;(async () => {
      try {
        await startMonitorsAutoRefresh({ interval_seconds: intervalSeconds })
        if (!cancelled) {
          // Reset initialization state when starting auto-refresh
          isInitializedRef.current = false
        }
      } catch (error) {
        console.warn('[useMonitorAutoSync] 启动显示器自动刷新失败', error)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [intervalSeconds])

  useTauriEvent<MonitorsChangedPayload>('monitors-changed', handleMonitorsChanged)
}
