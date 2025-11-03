/**
 * 权限引导弹窗组件
 */

import { useEffect, useState } from 'react'
import { X, RefreshCw, CheckCircle } from 'lucide-react'
import { usePermissionsStore } from '@/lib/stores/permissions'
import { PermissionItem } from './PermissionItem'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

export function PermissionsGuide() {
  const { t } = useTranslation()
  const {
    permissionsData,
    loading,
    hasChecked,
    userDismissed,
    checkPermissions,
    openSystemSettings,
    restartApp,
    dismissGuide
  } = usePermissionsStore()

  const [isVisible, setIsVisible] = useState(false)
  const [isRestarting, setIsRestarting] = useState(false)

  // 首次加载时检查权限
  useEffect(() => {
    if (!hasChecked) {
      checkPermissions()
    }
  }, [hasChecked, checkPermissions])

  // 根据权限状态决定是否显示引导
  useEffect(() => {
    if (permissionsData && !userDismissed) {
      // 如果权限未全部授予，显示引导
      setIsVisible(!permissionsData.allGranted)
    }
  }, [permissionsData, userDismissed])

  const handleOpenSettings = async (permissionType: string) => {
    try {
      await openSystemSettings(permissionType)
      toast.success(t('permissions.settingsOpened'))
    } catch (error) {
      toast.error(t('permissions.openSettingsFailed'))
    }
  }

  const handleRecheck = async () => {
    try {
      await checkPermissions()
      // 延迟一下再检查状态，确保 store 已更新
      setTimeout(() => {
        const currentData = usePermissionsStore.getState().permissionsData
        if (currentData?.allGranted) {
          toast.success(t('permissions.allGranted'))
        } else {
          toast.info(t('permissions.someNotGranted'))
        }
      }, 100)
    } catch (error) {
      toast.error(t('settings.permissionCheckFailed'))
    }
  }

  const handleRestart = async () => {
    try {
      setIsRestarting(true)
      toast.success(t('permissions.restarting'))
      await restartApp()
    } catch (error) {
      setIsRestarting(false)
      toast.error(t('permissions.restartFailed'))
    }
  }

  const handleDismiss = () => {
    dismissGuide()
    setIsVisible(false)
  }

  if (!isVisible || !permissionsData) {
    return null
  }

  const permissions = Object.values(permissionsData.permissions)
  const grantedCount = permissions.filter((p) => p.status === 'granted').length
  const totalCount = permissions.filter((p) => p.required).length
  const allGranted = permissionsData.allGranted

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <Card className="relative mx-4 max-h-[90vh] w-full max-w-2xl overflow-hidden shadow-2xl">
        {/* 关闭按钮 */}
        <button
          onClick={handleDismiss}
          className="hover:bg-accent absolute top-4 right-4 rounded-md p-1 transition-colors"
          aria-label="关闭">
          <X className="h-5 w-5" />
        </button>

        {/* 内容区域 */}
        <div className="flex max-h-[90vh] flex-col">
          {/* 头部 */}
          <div className="border-b p-6 pb-4">
            <h2 className="text-2xl font-semibold">{t('permissions.guide.title')}</h2>
            <p className="text-muted-foreground mt-2">{t('permissions.guide.description')}</p>

            {/* 进度指示 */}
            <div className="mt-4 flex items-center gap-3">
              <div className="flex-1">
                <div className="bg-secondary h-2 overflow-hidden rounded-full">
                  <div
                    className="bg-primary h-full transition-all duration-500"
                    style={{ width: `${(grantedCount / totalCount) * 100}%` }}
                  />
                </div>
              </div>
              <span className="text-muted-foreground text-sm font-medium">
                {grantedCount} / {totalCount}
              </span>
            </div>
          </div>

          {/* 权限列表 - 可滚动 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="space-y-4">
              {permissions.map((permission) => (
                <PermissionItem key={permission.type} permission={permission} onOpenSettings={handleOpenSettings} />
              ))}
            </div>
          </div>

          {/* 底部操作栏 */}
          <div className="bg-muted/30 border-t p-6">
            {allGranted ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle className="h-5 w-5" />
                  <span className="font-medium">{t('permissions.guide.allGrantedMessage')}</span>
                </div>
                <Button onClick={handleRestart} disabled={isRestarting} className="gap-2">
                  <RefreshCw className={`h-4 w-4 ${isRestarting ? 'animate-spin' : ''}`} />
                  {t('permissions.guide.restartApp')}
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-muted-foreground text-sm">{t('permissions.guide.instructionHint')}</p>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleRecheck} disabled={loading} className="gap-2">
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    {t('permissions.guide.recheck')}
                  </Button>
                  <Button onClick={handleDismiss} variant="ghost">
                    {t('permissions.guide.later')}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
