import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { usePermissionsStore } from '@/lib/stores/permissions'
import { PermissionItem } from '@/components/permissions/PermissionItem'
import { RefreshCw, Shield } from 'lucide-react'

export function PermissionsSettings() {
  const { t } = useTranslation()

  const permissionsData = usePermissionsStore((state) => state.permissionsData)
  const permissionsLoading = usePermissionsStore((state) => state.loading)
  const checkPermissions = usePermissionsStore((state) => state.checkPermissions)
  const openSystemSettings = usePermissionsStore((state) => state.openSystemSettings)

  // Check permissions when the component mounts (silent, no toast)
  useEffect(() => {
    // Run a silent check without success/failure toasts
    checkPermissions().catch(() => {
      // If it fails silently, the user can click the "Check permissions" button
    })
  }, [checkPermissions])

  const handleCheckPermissions = async () => {
    try {
      await checkPermissions()
      // Wait for the next render pass to ensure state is updated
      await new Promise((resolve) => setTimeout(resolve, 150))
      const currentData = usePermissionsStore.getState().permissionsData
      console.log('Permission check result:', currentData)
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
            {/* Permission overview */}
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
                <span className="text-muted-foreground text-xs">
                  {t('permissions.platform')}: {permissionsData.platform}
                </span>
                {permissionsData.needsRestart && (
                  <span className="text-xs text-yellow-600 dark:text-yellow-400">
                    {t('permissions.guide.allGrantedMessage')}
                  </span>
                )}
              </div>
            </div>

            {/* Permission list */}
            <div className="space-y-3">
              {Object.values(permissionsData.permissions).map((permission) => (
                <PermissionItem key={permission.type} permission={permission} onOpenSettings={handleOpenSettings} />
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
  )
}
