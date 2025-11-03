import { useSettingsStore } from '@/lib/stores/settings'
import { usePermissionsStore } from '@/lib/stores/permissions'
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
import { PermissionItem } from '@/components/permissions/PermissionItem'
import { RefreshCw, Shield } from 'lucide-react'

export default function SettingsView() {
  // 分别订阅各个字段，避免选择器返回新对象
  const settings = useSettingsStore((state) => state.settings)
  const fetchSettings = useSettingsStore((state) => state.fetchSettings)
  const updateDatabaseSettings = useSettingsStore((state) => state.updateDatabaseSettings)
  const updateScreenshotSettings = useSettingsStore((state) => state.updateScreenshotSettings)
  const updateLanguage = useSettingsStore((state) => state.updateLanguage)

  // 权限相关
  const permissionsData = usePermissionsStore((state) => state.permissionsData)
  const permissionsLoading = usePermissionsStore((state) => state.loading)
  const checkPermissions = usePermissionsStore((state) => state.checkPermissions)
  const openSystemSettings = usePermissionsStore((state) => state.openSystemSettings)

  // 调试：监听 permissionsData 变化
  useEffect(() => {
    if (permissionsData) {
      console.log('📊 设置页面 - permissionsData 更新:', {
        allGranted: permissionsData.allGranted,
        platform: permissionsData.platform,
        needsRestart: permissionsData.needsRestart,
        permissions: Object.keys(permissionsData.permissions)
      })
    }
  }, [permissionsData])

  const [formData, setFormData] = useState({
    database: settings.database,
    screenshot: settings.screenshot
  })
  const { t, i18n } = useTranslation()

  // 组件挂载时加载后端配置
  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  // 组件挂载时检查权限（静默检查，不显示 toast）
  useEffect(() => {
    // 静默检查权限，不显示成功/失败提示
    checkPermissions().catch(() => {
      // 静默失败，用户可以手动点击"检查权限"按钮
    })
  }, [])

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

  const handleCheckPermissions = async () => {
    try {
      await checkPermissions()
      // 等待下一个渲染周期，确保状态已更新
      await new Promise((resolve) => setTimeout(resolve, 150))
      const currentData = usePermissionsStore.getState().permissionsData
      console.log('权限检查结果:', currentData)
      if (currentData?.allGranted) {
        toast.success(t('settings.permissionCheckSuccess'))
      } else {
        toast.warning(t('permissions.someNotGranted'))
      }
    } catch (error) {
      toast.error(t('settings.permissionCheckFailed'))
      console.error('Check permissions failed:', error)
    }
  }

  const handleOpenSettings = async (permissionType: string) => {
    try {
      await openSystemSettings(permissionType)
      toast.success(t('permissions.settingsOpened'))
    } catch (error) {
      toast.error(t('permissions.openSettingsFailed'))
    }
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

          {/* 系统权限管理 */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    {t('settings.permissions')}
                  </CardTitle>
                  <CardDescription>{t('settings.permissionsDescription')}</CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCheckPermissions}
                  disabled={permissionsLoading}
                  className="gap-2">
                  <RefreshCw className={`h-4 w-4 ${permissionsLoading ? 'animate-spin' : ''}`} />
                  {t('settings.checkPermissions')}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {permissionsData ? (
                <div className="space-y-4">
                  {/* 权限状态概览 */}
                  <div className="bg-muted/50 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{t('permissions.allGranted')}:</span>
                      <span
                        className={`text-sm font-semibold ${
                          permissionsData.allGranted
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-yellow-600 dark:text-yellow-400'
                        }`}>
                        {permissionsData.allGranted ? t('common.success') : t('permissions.someNotGranted')}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-muted-foreground text-xs">平台: {permissionsData.platform}</span>
                      {permissionsData.needsRestart && (
                        <span className="text-xs text-yellow-600 dark:text-yellow-400">
                          {t('permissions.guide.allGrantedMessage')}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 权限列表 */}
                  <div className="space-y-3">
                    {Object.values(permissionsData.permissions).map((permission) => (
                      <PermissionItem
                        key={permission.type}
                        permission={permission}
                        onOpenSettings={handleOpenSettings}
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <Shield className="text-muted-foreground mb-3 h-12 w-12" />
                  <p className="text-muted-foreground text-sm">{t('settings.permissionChecking')}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCheckPermissions}
                    disabled={permissionsLoading}
                    className="mt-4 gap-2">
                    <RefreshCw className={`h-4 w-4 ${permissionsLoading ? 'animate-spin' : ''}`} />
                    {t('settings.checkPermissions')}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
