import { useSettingsStore } from '@/lib/stores/settings'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { languages } from '@/locales'
import { toast } from 'sonner'
import ModelManagement from '@/components/models/ModelManagement'

export default function SettingsView() {
  // 分别订阅各个字段，避免选择器返回新对象
  const settings = useSettingsStore((state) => state.settings)
  const fetchSettings = useSettingsStore((state) => state.fetchSettings)
  const updateDatabaseSettings = useSettingsStore((state) => state.updateDatabaseSettings)
  const updateScreenshotSettings = useSettingsStore((state) => state.updateScreenshotSettings)
  const updateLanguage = useSettingsStore((state) => state.updateLanguage)
  const [formData, setFormData] = useState({
    database: settings.database,
    screenshot: settings.screenshot
  })
  const { t, i18n } = useTranslation()

  // 组件挂载时加载后端配置
  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  // 当 settings 更新时，同步 formData
  useEffect(() => {
    setFormData({
      database: settings.database,
      screenshot: settings.screenshot
    })
  }, [settings])

  const handleSave = async () => {
    try {
      let hasError = false
      const errors: string[] = []

      // 更新数据库路径
      if (formData.database?.path) {
        try {
          await updateDatabaseSettings(formData.database)
        } catch (error) {
          hasError = true
          errors.push(t('settings.failedToUpdateDatabase'))
        }
      }

      // 更新截屏路径
      if (formData.screenshot?.savePath) {
        try {
          await updateScreenshotSettings(formData.screenshot)
        } catch (error) {
          hasError = true
          errors.push(t('settings.failedToUpdateScreenshot'))
        }
      }

      // 显示提示（Sonner 会根据 Toaster 设置的主题自动适配暗色/亮色）
      if (hasError) {
        toast.error(errors.join('; '))
      } else {
        toast.success(t('settings.savedSuccessfully'))
      }
    } catch (error) {
      toast.error(t('settings.saveFailed'))
      console.error('Save settings failed:', error)
    }
  }

  const handleLanguageChange = (value: string) => {
    i18n.changeLanguage(value)
    updateLanguage(value as 'zh-CN' | 'en-US')
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <h1 className="text-2xl font-semibold">{t('settings.title')}</h1>
        <p className="text-muted-foreground mt-1 text-sm">{t('settings.description')}</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl space-y-6">
          {/* 模型管理 */}
          <ModelManagement />

          {/* 通用设置 */}
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.general')}</CardTitle>
              <CardDescription>{t('settings.generalDescription')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="language">{t('settings.language')}</Label>
                <Select value={i18n.language} onValueChange={handleLanguageChange}>
                  <SelectTrigger id="language">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {languages.map((lang) => (
                      <SelectItem key={lang.code} value={lang.code}>
                        {lang.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* 数据库设置 */}
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
                  value={formData.database?.path || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      database: { path: e.target.value }
                    })
                  }
                  placeholder={t('settings.databasePathPlaceholder')}
                />
              </div>

              <Button onClick={handleSave}>{t('settings.saveSettings')}</Button>
            </CardContent>
          </Card>

          {/* 截屏设置 */}
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
                  value={formData.screenshot?.savePath || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      screenshot: { savePath: e.target.value }
                    })
                  }
                  placeholder={t('settings.screenshotPathPlaceholder')}
                />
              </div>

              <Button onClick={handleSave}>{t('settings.saveSettings')}</Button>
            </CardContent>
          </Card>

          {/* 外观设置 */}
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
        </div>
      </div>
    </div>
  )
}
