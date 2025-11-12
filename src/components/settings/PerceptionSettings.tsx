import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { getPerceptionSettings, updatePerceptionSettings } from '@/lib/client/screens'
import { Keyboard, Mouse } from 'lucide-react'

interface PerceptionSettingsData {
  keyboard_enabled: boolean
  mouse_enabled: boolean
}

export function PerceptionSettings() {
  const { t } = useTranslation()
  const [settings, setSettings] = useState<PerceptionSettingsData>({
    keyboard_enabled: true,
    mouse_enabled: true
  })
  const [isLoading, setIsLoading] = useState(false)

  // Load perception settings
  const loadSettings = async () => {
    setIsLoading(true)
    try {
      const response: any = await getPerceptionSettings()
      if (response?.success && response.data) {
        setSettings({
          keyboard_enabled: response.data.keyboard_enabled ?? true,
          mouse_enabled: response.data.mouse_enabled ?? true
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
    const newSettings = { ...settings, keyboard_enabled: enabled }
    setSettings(newSettings)

    try {
      const response: any = await updatePerceptionSettings({ keyboard_enabled: enabled })
      if (response?.success) {
        toast.success(t('settings.savedSuccessfully'))
      } else {
        // Revert on failure
        setSettings(settings)
        toast.error(response?.error || t('settings.saveFailed'))
      }
    } catch (error) {
      // Revert on failure
      setSettings(settings)
      toast.error(t('settings.saveFailed'))
    }
  }

  // Update mouse setting
  const handleMouseToggle = async (enabled: boolean) => {
    const newSettings = { ...settings, mouse_enabled: enabled }
    setSettings(newSettings)

    try {
      const response: any = await updatePerceptionSettings({ mouse_enabled: enabled })
      if (response?.success) {
        toast.success(t('settings.savedSuccessfully'))
      } else {
        // Revert on failure
        setSettings(settings)
        toast.error(response?.error || t('settings.saveFailed'))
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
            checked={settings.keyboard_enabled}
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
            checked={settings.mouse_enabled}
            onCheckedChange={handleMouseToggle}
            disabled={isLoading}
          />
        </div>
      </CardContent>
    </Card>
  )
}
