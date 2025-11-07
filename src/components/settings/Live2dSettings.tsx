import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import { useEffect, useState, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useLive2dStore } from '@/lib/stores/live2d'

export function Live2dSettings() {
  const { t } = useTranslation()
  const [newRemoteUrl, setNewRemoteUrl] = useState('')
  const [localDuration, setLocalDuration] = useState<number>(5000)
  const debounceTimerRef = useRef<NodeJS.Timeout | undefined>(undefined)

  const live2dState = useLive2dStore((state) => state.state)
  const live2dLoading = useLive2dStore((state) => state.loading)
  const fetchLive2d = useLive2dStore((state) => state.fetch)
  const toggleLive2d = useLive2dStore((state) => state.setEnabled)
  const selectLive2dModel = useLive2dStore((state) => state.selectModel)
  const addLive2dRemote = useLive2dStore((state) => state.addRemoteModel)
  const removeLive2dRemote = useLive2dStore((state) => state.removeRemoteModel)
  const setNotificationDuration = useLive2dStore((state) => state.setNotificationDuration)

  // 组件挂载时加载 Live2D 配置
  useEffect(() => {
    fetchLive2d().catch((error) => {
      console.error('加载 Live2D 配置失败', error)
    })
  }, [fetchLive2d])

  // 同步 store 的值到本地状态
  useEffect(() => {
    setLocalDuration(live2dState.settings.notificationDuration)
  }, [live2dState.settings.notificationDuration])

  // 清理定时器
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [])

  const live2dSettingsData = live2dState.settings
  const live2dModels = live2dState.models

  const handleLive2dToggle = async (value: boolean) => {
    try {
      await toggleLive2d(value)
      toast.success(value ? t('live2d.enabled') : t('live2d.disabled'))
    } catch (error) {
      toast.error(t('live2d.updateFailed'))
    }
  }

  const handleLive2dModelChange = async (modelUrl: string) => {
    try {
      await selectLive2dModel(modelUrl)
      toast.success(t('live2d.modelSwitched'))
    } catch (error) {
      toast.error(t('live2d.updateFailed'))
    }
  }

  const handleAddLive2dRemote = async () => {
    if (!newRemoteUrl.trim()) return
    try {
      await addLive2dRemote(newRemoteUrl.trim())
      toast.success(t('live2d.remoteAdded'))
      setNewRemoteUrl('')
    } catch (error) {
      toast.error(t('live2d.updateFailed'))
    }
  }

  const handleRemoveLive2dRemote = async (url: string) => {
    try {
      await removeLive2dRemote(url)
      toast.success(t('live2d.remoteRemoved'))
    } catch (error) {
      toast.error(t('live2d.updateFailed'))
    }
  }

  const handleNotificationDurationChange = useCallback(
    (values: number[]) => {
      const duration = values[0]

      // 立即更新本地显示的值
      setLocalDuration(duration)

      // 清除之前的定时器
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }

      // 设置防抖：500ms 后才真正调用 API
      debounceTimerRef.current = setTimeout(() => {
        setNotificationDuration(duration)
          .then(() => {
            toast.success(t('live2d.notificationDurationUpdated'))
          })
          .catch((error) => {
            console.error('更新通知时长失败', error)
            toast.error(t('live2d.updateFailed'))
            // 失败时恢复原值
            setLocalDuration(live2dState.settings.notificationDuration)
          })
      }, 500)
    },
    [setNotificationDuration, t, live2dState.settings.notificationDuration]
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('live2d.title')}</CardTitle>
        <CardDescription>{t('live2d.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <p className="font-medium">{t('live2d.enableTitle')}</p>
            <p className="text-muted-foreground text-sm">{t('live2d.enableDescription')}</p>
          </div>
          <Switch checked={live2dSettingsData.enabled} disabled={live2dLoading} onCheckedChange={handleLive2dToggle} />
        </div>

        <div className="space-y-2">
          <Label>{t('live2d.currentModel')}</Label>
          <Select
            value={live2dSettingsData.selectedModelUrl}
            onValueChange={handleLive2dModelChange}
            disabled={!live2dSettingsData.enabled || live2dLoading || live2dModels.length === 0}>
            <SelectTrigger>
              <SelectValue placeholder={t('live2d.selectPlaceholder')} />
            </SelectTrigger>
            <SelectContent>
              {live2dModels.map((model) => (
                <SelectItem value={model.url} key={model.url}>
                  <div className="flex flex-col">
                    <span>{model.name || model.url}</span>
                    <span className="text-muted-foreground text-xs">
                      {model.type === 'local' ? t('live2d.modelLocal') : t('live2d.modelRemote')}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-muted-foreground text-xs">{t('live2d.modelHint')}</p>
        </div>

        <div className="space-y-2">
          <Label>{t('live2d.remoteManage')}</Label>
          <div className="flex gap-2">
            <Input
              value={newRemoteUrl}
              onChange={(event) => setNewRemoteUrl(event.target.value)}
              placeholder="https://example.com/model.json"
              disabled={live2dLoading}
            />
            <Button onClick={handleAddLive2dRemote} disabled={live2dLoading || !newRemoteUrl.trim()}>
              {t('live2d.addRemote')}
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {live2dSettingsData.remoteModels.map((url) => (
              <Badge key={url} variant="outline" className="flex items-center gap-2">
                <span className="max-w-[200px] truncate" title={url}>
                  {url}
                </span>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-destructive text-xs"
                  onClick={() => handleRemoveLive2dRemote(url)}
                  disabled={live2dLoading}>
                  {t('live2d.remove')}
                </button>
              </Badge>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>{t('live2d.notificationDuration')}</Label>
            <span className="text-muted-foreground text-sm">{(localDuration / 1000).toFixed(1)}s</span>
          </div>
          <Slider
            value={[localDuration]}
            onValueChange={handleNotificationDurationChange}
            min={1000}
            max={30000}
            step={1000}
            disabled={live2dLoading}
            className="w-full"
          />
          <p className="text-muted-foreground text-xs">{t('live2d.notificationDurationHint')}</p>
        </div>
      </CardContent>
    </Card>
  )
}
