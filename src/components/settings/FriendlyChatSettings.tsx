import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useFriendlyChatStore } from '@/lib/stores/friendlyChat'
import { useLive2dStore } from '@/lib/stores/live2d'
import { useEffect, useState } from 'react'

export function FriendlyChatSettings() {
  const { t } = useTranslation()

  const friendlyChatSettings = useFriendlyChatStore((state) => state.settings)
  const friendlyChatLoading = useFriendlyChatStore((state) => state.loading)
  const fetchFriendlyChatSettings = useFriendlyChatStore((state) => state.fetchSettings)
  const updateFriendlyChatSettings = useFriendlyChatStore((state) => state.updateSettings)

  // Local state for displaying updates immediately
  const [localInterval, setLocalInterval] = useState<number | null>(null)
  const [localDataWindow, setLocalDataWindow] = useState<number | null>(null)

  const live2dSettingsData = useLive2dStore((state) => state.state.settings)

  // Load friendly chat configuration on mount
  useEffect(() => {
    fetchFriendlyChatSettings().catch((error) => {
      console.error('Failed to load friendly chat configuration', error)
    })
  }, [fetchFriendlyChatSettings])

  const handleFriendlyChatToggle = async (value: boolean) => {
    try {
      await updateFriendlyChatSettings({ enabled: value })
      toast.success(value ? t('friendlyChat.toast.enabled') : t('friendlyChat.toast.disabled'))
    } catch (error) {
      toast.error(t('friendlyChat.toast.updateFailed'))
    }
  }

  const handleFriendlyChatIntervalChange = async (value: number[]) => {
    setLocalInterval(null)
    try {
      await updateFriendlyChatSettings({ interval: value[0] })
      toast.success(t('friendlyChat.toast.intervalUpdated'))
    } catch (error) {
      toast.error(t('friendlyChat.toast.updateFailed'))
    }
  }

  const handleFriendlyChatDataWindowChange = async (value: number[]) => {
    setLocalDataWindow(null)
    try {
      await updateFriendlyChatSettings({ dataWindow: value[0] })
      toast.success(t('friendlyChat.toast.dataWindowUpdated'))
    } catch (error) {
      toast.error(t('friendlyChat.toast.updateFailed'))
    }
  }

  const handleFriendlyChatNotificationToggle = async (value: boolean) => {
    try {
      await updateFriendlyChatSettings({ enableSystemNotification: value })
      toast.success(value ? t('friendlyChat.toast.notificationEnabled') : t('friendlyChat.toast.notificationDisabled'))
    } catch (error) {
      toast.error(t('friendlyChat.toast.notificationUpdateFailed'))
    }
  }

  const handleFriendlyChatLive2dToggle = async (value: boolean) => {
    try {
      await updateFriendlyChatSettings({ enableLive2dDisplay: value })
      toast.success(value ? t('friendlyChat.toast.live2dEnabled') : t('friendlyChat.toast.live2dDisabled'))
    } catch (error) {
      toast.error(t('friendlyChat.toast.live2dUpdateFailed'))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('friendlyChat.title')}</CardTitle>
        <CardDescription>{t('friendlyChat.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Enable switch */}
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <p className="font-medium">{t('friendlyChat.enableTitle')}</p>
            <p className="text-muted-foreground text-sm">{t('friendlyChat.enableDescription')}</p>
          </div>
          <Switch
            checked={friendlyChatSettings.enabled}
            disabled={friendlyChatLoading}
            onCheckedChange={handleFriendlyChatToggle}
          />
        </div>

        {/* Conversation interval */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>{t('friendlyChat.intervalTitle')}</Label>
            <span className="text-muted-foreground text-sm">
              {localInterval ?? friendlyChatSettings.interval} {t('friendlyChat.minutes')}
            </span>
          </div>
          <Slider
            value={[localInterval ?? friendlyChatSettings.interval]}
            onValueChange={(value) => setLocalInterval(value[0])}
            onValueCommit={handleFriendlyChatIntervalChange}
            min={1}
            max={120}
            step={1}
            disabled={!friendlyChatSettings.enabled || friendlyChatLoading}
            className="w-full"
          />
          <p className="text-muted-foreground text-xs">{t('friendlyChat.intervalDescription')}</p>
        </div>

        {/* Data window */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>{t('friendlyChat.dataWindowTitle')}</Label>
            <span className="text-muted-foreground text-sm">
              {localDataWindow ?? friendlyChatSettings.dataWindow} {t('friendlyChat.minutes')}
            </span>
          </div>
          <Slider
            value={[localDataWindow ?? friendlyChatSettings.dataWindow]}
            onValueChange={(value) => setLocalDataWindow(value[0])}
            onValueCommit={handleFriendlyChatDataWindowChange}
            min={5}
            max={120}
            step={5}
            disabled={!friendlyChatSettings.enabled || friendlyChatLoading}
            className="w-full"
          />
          <p className="text-muted-foreground text-xs">{t('friendlyChat.dataWindowDescription')}</p>
        </div>

        {/* System notifications */}
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <p className="font-medium">{t('friendlyChat.notificationTitle')}</p>
            <p className="text-muted-foreground text-sm">{t('friendlyChat.notificationDescription')}</p>
          </div>
          <Switch
            checked={friendlyChatSettings.enableSystemNotification}
            disabled={!friendlyChatSettings.enabled || friendlyChatLoading}
            onCheckedChange={handleFriendlyChatNotificationToggle}
          />
        </div>

        {/* Live2D visibility */}
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div className="flex-1">
            <p className="font-medium">{t('friendlyChat.live2dTitle')}</p>
            <p className="text-muted-foreground text-sm">
              {t('friendlyChat.live2dDescription')}
              {!live2dSettingsData.enabled && (
                <span className="text-yellow-600 dark:text-yellow-500">
                  {' '}
                  （{t('friendlyChat.live2dRequiresEnabled')}）
                </span>
              )}
            </p>
          </div>
          <Switch
            checked={friendlyChatSettings.enableLive2dDisplay && live2dSettingsData.enabled}
            disabled={!friendlyChatSettings.enabled || friendlyChatLoading || !live2dSettingsData.enabled}
            onCheckedChange={handleFriendlyChatLive2dToggle}
          />
        </div>
      </CardContent>
    </Card>
  )
}
