import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { getMonitors, getScreenSettings, updateScreenSettings, captureAllPreviews } from '@/lib/client/screens'
import type { MonitorInfo, ScreenSetting } from '@/lib/types/settings'
import { ScreenCard } from './ScreenCard'

export function ScreenSelectionSettings() {
  const { t } = useTranslation()
  const [monitors, setMonitors] = useState<MonitorInfo[]>([])
  const [screenSettings, setScreenSettings] = useState<ScreenSetting[]>([])
  const [isLoadingScreens, setIsLoadingScreens] = useState(false)
  const [monitorPreviews, setMonitorPreviews] = useState<Map<number, string>>(new Map())

  // 加载屏幕信息（列表 + 已保存的选择 + 预览）
  const loadScreenInfo = async () => {
    setIsLoadingScreens(true)
    try {
      const monitorsResponse: any = await getMonitors()
      if (monitorsResponse?.success && monitorsResponse.data?.monitors) {
        setMonitors(monitorsResponse.data.monitors as MonitorInfo[])
      }

      const settingsResponse: any = await getScreenSettings()
      if (settingsResponse?.success && settingsResponse.data?.screens) {
        setScreenSettings(settingsResponse.data.screens as ScreenSetting[])
      }

      // 抓取所有显示器预览图
      if (monitorsResponse?.success && monitorsResponse.data?.monitors?.length > 0) {
        const resp: any = await captureAllPreviews()
        if (resp?.success && resp.data?.previews) {
          const map = new Map<number, string>()
          resp.data.previews.forEach((p: any) => {
            if (p.image_base64) map.set(p.monitor_index, p.image_base64)
          })
          setMonitorPreviews(map)
        }
      }
    } finally {
      setIsLoadingScreens(false)
    }
  }

  // 组件挂载时加载多显示器信息
  useEffect(() => {
    loadScreenInfo().catch((err) => console.error('加载屏幕信息失败:', err))
  }, [])

  // 当显示器列表加载完成但没有设置时，初始化默认设置
  useEffect(() => {
    initializeScreenSettings()
  }, [monitors])

  // 切换屏幕选择
  const handleScreenToggle = async (monitorIndex: number, enabled: boolean) => {
    const monitor = monitors.find((m) => m.index === monitorIndex)
    if (!monitor) return

    // Update local state immediately for UI responsiveness
    setScreenSettings((prev) => {
      const existing = prev.find((s) => s.monitor_index === monitorIndex)
      const newSetting: ScreenSetting = {
        monitor_index: monitor.index,
        monitor_name: monitor.name,
        is_enabled: enabled,
        resolution: monitor.resolution,
        is_primary: monitor.is_primary
      }
      if (existing) {
        return prev.map((s) => (s.monitor_index === monitorIndex ? newSetting : s))
      }
      return [...prev, newSetting]
    })

    // Auto-save the change to backend immediately
    try {
      setScreenSettings((prevSettings) => {
        // Build complete settings based on the updated state
        const allSettings = monitors.map((m) => {
          if (m.index === monitorIndex) {
            return {
              monitor_index: m.index,
              monitor_name: m.name,
              is_enabled: enabled,
              resolution: m.resolution,
              is_primary: m.is_primary
            }
          }
          const existing = prevSettings.find((s) => s.monitor_index === m.index)
          return (
            existing || {
              monitor_index: m.index,
              monitor_name: m.name,
              is_enabled: m.is_primary,
              resolution: m.resolution,
              is_primary: m.is_primary
            }
          )
        })

        // Fire off the async save without blocking UI updates
        ;(async () => {
          try {
            await updateScreenSettings({ screens: allSettings as any[] })
          } catch (error) {
            console.error('[ScreenSelectionSettings] 自动保存屏幕设置失败', error)
            toast.error(t('settings.autoSaveFailed'))
          }
        })()

        return prevSettings
      })
    } catch (error) {
      console.error('[ScreenSelectionSettings] 屏幕切换失败', error)
    }
  }

  // 保存屏幕设置（手动保存按钮 - 用于保存任何手动修改）
  const handleSaveScreenSettings = async () => {
    if (monitors.length === 0) return
    // Build complete settings with all monitors to ensure consistency
    const allSettings = monitors.map((m) => {
      const existing = screenSettings.find((s) => s.monitor_index === m.index)
      return (
        existing || {
          monitor_index: m.index,
          monitor_name: m.name,
          is_enabled: m.is_primary,
          resolution: m.resolution,
          is_primary: m.is_primary
        }
      )
    })
    const resp: any = await updateScreenSettings({ screens: allSettings as any[] })
    if (resp?.success) {
      // Reload to sync with backend after manual save
      await loadScreenInfo()
      toast.success(t('settings.savedSuccessfully'))
    } else {
      toast.error(resp?.error || t('settings.saveFailed'))
    }
  }

  // 重置为仅主屏
  const handleResetScreenSettings = async () => {
    const defaults = monitors.map((m) => ({
      monitor_index: m.index,
      monitor_name: m.name,
      is_enabled: m.is_primary,
      resolution: m.resolution,
      is_primary: m.is_primary
    }))
    const resp: any = await updateScreenSettings({ screens: defaults as any[] })
    if (resp?.success) {
      setScreenSettings(defaults as ScreenSetting[])
      toast.success(t('settings.savedSuccessfully'))
    } else {
      toast.error(resp?.error || t('settings.saveFailed'))
    }
  }

  // 初始化屏幕设置 - 确保有默认值
  const initializeScreenSettings = () => {
    if (monitors.length > 0 && screenSettings.length === 0) {
      const defaults = monitors.map((m) => ({
        monitor_index: m.index,
        monitor_name: m.name,
        is_enabled: m.is_primary,
        resolution: m.resolution,
        is_primary: m.is_primary
      }))
      setScreenSettings(defaults as ScreenSetting[])
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.screenSelection')}</CardTitle>
        <CardDescription>{t('settings.screenSelectionDescription')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>{t('settings.availableScreens')}</Label>
            <Button variant="outline" size="sm" onClick={loadScreenInfo} disabled={isLoadingScreens}>
              {isLoadingScreens ? t('common.loading') : t('common.refresh')}
            </Button>
          </div>

          {monitors.length === 0 ? (
            <p className="text-muted-foreground text-sm">{t('settings.noScreensFound')}</p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {monitors.map((monitor) => {
                const setting = screenSettings.find((s) => s.monitor_index === monitor.index)
                const preview = monitorPreviews.get(monitor.index)
                const isLoadingPreview = isLoadingScreens && !preview
                return (
                  <ScreenCard
                    key={monitor.index}
                    monitor={monitor}
                    setting={setting}
                    preview={preview}
                    onToggle={handleScreenToggle}
                    isLoadingPreview={isLoadingPreview}
                  />
                )
              })}
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <Button onClick={handleSaveScreenSettings}>{t('settings.saveScreenSettings')}</Button>
          <Button variant="outline" onClick={handleResetScreenSettings}>
            {t('settings.resetToDefault')}
          </Button>
        </div>

        {screenSettings.length > 0 && (
          <div className="text-muted-foreground text-sm">
            {t('settings.selectedScreens', {
              count: screenSettings.filter((s) => s.is_enabled).length
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
