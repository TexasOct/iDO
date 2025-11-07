import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useSettingsStore } from '@/lib/stores/settings'

export function ScreenshotSettings() {
  const { t } = useTranslation()
  const settings = useSettingsStore((state) => state.settings)
  const updateScreenshotSettings = useSettingsStore((state) => state.updateScreenshotSettings)

  const [screenshotPath, setScreenshotPath] = useState(settings.screenshot?.savePath || '')

  useEffect(() => {
    setScreenshotPath(settings.screenshot?.savePath || '')
  }, [settings.screenshot?.savePath])

  const handleSave = async () => {
    if (!screenshotPath) {
      toast.error(t('settings.saveFailed'))
      return
    }

    try {
      await updateScreenshotSettings({ savePath: screenshotPath })
      toast.success(t('settings.savedSuccessfully'))
    } catch (error) {
      toast.error(t('settings.failedToUpdateScreenshot'))
      console.error('Save screenshot settings failed:', error)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.screenshot')}</CardTitle>
        <CardDescription>{t('settings.screenshotDescription')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="screenshotPath">{t('settings.screenshotPath')}</Label>
          <Input
            id="screenshotPath"
            value={screenshotPath}
            onChange={(e) => setScreenshotPath(e.target.value)}
            placeholder={t('settings.screenshotPathPlaceholder')}
          />
        </div>

        <Button onClick={handleSave}>{t('settings.saveSettings')}</Button>
      </CardContent>
    </Card>
  )
}
