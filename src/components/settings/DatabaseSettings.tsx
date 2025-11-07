import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useSettingsStore } from '@/lib/stores/settings'

export function DatabaseSettings() {
  const { t } = useTranslation()
  const settings = useSettingsStore((state) => state.settings)
  const updateDatabaseSettings = useSettingsStore((state) => state.updateDatabaseSettings)

  const [databasePath, setDatabasePath] = useState(settings.database?.path || '')

  useEffect(() => {
    setDatabasePath(settings.database?.path || '')
  }, [settings.database?.path])

  const handleSave = async () => {
    if (!databasePath) {
      toast.error(t('settings.saveFailed'))
      return
    }

    try {
      await updateDatabaseSettings({ path: databasePath })
      toast.success(t('settings.savedSuccessfully'))
    } catch (error) {
      toast.error(t('settings.failedToUpdateDatabase'))
      console.error('Save database settings failed:', error)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.database')}</CardTitle>
        <CardDescription>{t('settings.databaseDescription')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="databasePath">{t('settings.databasePath')}</Label>
          <Input
            id="databasePath"
            value={databasePath}
            onChange={(e) => setDatabasePath(e.target.value)}
            placeholder={t('settings.databasePathPlaceholder')}
          />
        </div>

        <Button onClick={handleSave}>{t('settings.saveSettings')}</Button>
      </CardContent>
    </Card>
  )
}
