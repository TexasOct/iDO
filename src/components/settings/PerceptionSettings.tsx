import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { getPerceptionSettings, updatePerceptionSettings } from '@/lib/client/apiClient'
import { Keyboard, Mouse } from 'lucide-react'

interface PerceptionSettingsData {
  keyboardEnabled: boolean
  mouseEnabled: boolean
}

interface PerceptionSettingsResponse {
  success?: boolean
  data?: {
    keyboardEnabled?: boolean
    mouseEnabled?: boolean
    keyboard_enabled?: boolean
    mouse_enabled?: boolean
  }
}

export function PerceptionSettings() {
  const { t } = useTranslation()
  const [settings, setSettings] = useState<PerceptionSettingsData>({
    keyboardEnabled: true,
    mouseEnabled: true
  })
  const [isLoading, setIsLoading] = useState(false)

  // Load perception settings
  const loadSettings = async () => {
    setIsLoading(true)
    try {
      const response = (await getPerceptionSettings()) as PerceptionSettingsResponse
      if (response?.success && response.data) {
        const keyboardEnabled = response.data.keyboardEnabled ?? response.data.keyboard_enabled ?? true
        const mouseEnabled = response.data.mouseEnabled ?? response.data.mouse_enabled ?? true
        setSettings({
          keyboardEnabled,
          mouseEnabled
        })
      }
    } catch (error) {
      console.error('Failed to load perception settings:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Load settings on mount
  useEffect(() => {
    loadSettings().catch((err) => console.error('Failed to load perception settings:', err))
  }, [])

  // Update keyboard setting
  const handleKeyboardToggle = async (enabled: boolean) => {
    const newSettings = { ...settings, keyboardEnabled: enabled }
    setSettings(newSettings)

    try {
      const response = await updatePerceptionSettings({ keyboardEnabled: enabled })
      if (response?.success) {
        toast.success(t('settings.savedSuccessfully'))
      } else {
        // Revert on failure
        setSettings(settings)
        const errorMsg = typeof response?.error === 'string' ? response.error : t('settings.saveFailed')
        toast.error(errorMsg)
      }
    } catch (error) {
      // Revert on failure
      setSettings(settings)
      toast.error(t('settings.saveFailed'))
    }
  }

  // Update mouse setting
  const handleMouseToggle = async (enabled: boolean) => {
    const newSettings = { ...settings, mouseEnabled: enabled }
    setSettings(newSettings)

    try {
      const response = await updatePerceptionSettings({ mouseEnabled: enabled })
      if (response?.success) {
        toast.success(t('settings.savedSuccessfully'))
      } else {
        // Revert on failure
        setSettings(settings)
        const errorMsg = typeof response?.error === 'string' ? response.error : t('settings.saveFailed')
        toast.error(errorMsg)
      }
    } catch (error) {
      // Revert on failure
      setSettings(settings)
      toast.error(t('settings.saveFailed'))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.perceptionSettings')}</CardTitle>
        <CardDescription>{t('settings.perceptionSettingsDescription')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Keyboard perception toggle */}
        <div className="flex items-center justify-between space-x-4">
          <div className="flex flex-1 items-center space-x-3">
            <div className="bg-primary/10 rounded-lg p-2">
              <Keyboard className="text-primary h-5 w-5" />
            </div>
            <div className="space-y-0.5">
              <Label htmlFor="keyboard-toggle" className="cursor-pointer text-base font-medium">
                {t('settings.keyboardPerception')}
              </Label>
              <p className="text-muted-foreground text-sm">{t('settings.keyboardPerceptionDescription')}</p>
            </div>
          </div>
          <Switch
            id="keyboard-toggle"
            checked={settings.keyboardEnabled}
            onCheckedChange={handleKeyboardToggle}
            disabled={isLoading}
          />
        </div>

        {/* Mouse perception toggle */}
        <div className="flex items-center justify-between space-x-4">
          <div className="flex flex-1 items-center space-x-3">
            <div className="bg-primary/10 rounded-lg p-2">
              <Mouse className="text-primary h-5 w-5" />
            </div>
            <div className="space-y-0.5">
              <Label htmlFor="mouse-toggle" className="cursor-pointer text-base font-medium">
                {t('settings.mousePerception')}
              </Label>
              <p className="text-muted-foreground text-sm">{t('settings.mousePerceptionDescription')}</p>
            </div>
          </div>
          <Switch
            id="mouse-toggle"
            checked={settings.mouseEnabled}
            onCheckedChange={handleMouseToggle}
            disabled={isLoading}
          />
        </div>
      </CardContent>
    </Card>
  )
}
