import { useSettingsStore } from '@/lib/stores/settings'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { languages } from '@/locales'

export default function SettingsView() {
  const { settings, updateLLMSettings, updateLanguage } = useSettingsStore()
  const [formData, setFormData] = useState(settings.llm)
  const { t, i18n } = useTranslation()

  const handleSave = async () => {
    await updateLLMSettings(formData)
  }

  const handleLanguageChange = (value: string) => {
    i18n.changeLanguage(value)
    updateLanguage(value as 'zh-CN' | 'en-US')
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <h1 className="text-2xl font-semibold">{t('settings.title')}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t('settings.description')}</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl space-y-6">
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

          {/* LLM 设置 */}
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.llm')}</CardTitle>
              <CardDescription>{t('settings.llmDescription')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="baseUrl">{t('settings.baseUrl')}</Label>
                <Input
                  id="baseUrl"
                  value={formData.baseUrl}
                  onChange={(e) => setFormData({ ...formData, baseUrl: e.target.value })}
                  placeholder="https://api.openai.com/v1"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="apiKey">{t('settings.apiKey')}</Label>
                <Input
                  id="apiKey"
                  type="password"
                  value={formData.apiKey}
                  onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                  placeholder="sk-..."
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="model">{t('settings.model')}</Label>
                <Input id="model" value={formData.model} onChange={(e) => setFormData({ ...formData, model: e.target.value })} placeholder="gpt-4" />
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
                <p className="text-sm text-muted-foreground">{t(`theme.${settings.theme}`)}</p>
                {/* TODO: 添加主题切换器 */}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
