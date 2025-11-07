import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { useTranslation } from 'react-i18next'
import { useSettingsStore } from '@/lib/stores/settings'

export function AppearanceSettings() {
  const { t } = useTranslation()
  const settings = useSettingsStore((state) => state.settings)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.appearance')}</CardTitle>
        <CardDescription>{t('settings.appearanceDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <Label>{t('settings.theme')}</Label>
          <p className="text-muted-foreground text-sm">{t(`theme.${settings.theme}`)}</p>
          {/* TODO: 添加主题切换器 */}
        </div>
      </CardContent>
    </Card>
  )
}
