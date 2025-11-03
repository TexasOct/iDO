/**
 * 单个权限项组件
 */

import { CheckCircle2, XCircle, AlertCircle, ExternalLink } from 'lucide-react'
import type { PermissionInfo } from '@/lib/types/permissions'
import { PermissionStatus } from '@/lib/types/permissions'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'

interface PermissionItemProps {
  permission: PermissionInfo
  onOpenSettings: (permissionType: string) => void
}

export function PermissionItem({ permission, onOpenSettings }: PermissionItemProps) {
  const { t } = useTranslation()

  const getStatusIcon = () => {
    switch (permission.status) {
      case PermissionStatus.GRANTED:
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case PermissionStatus.DENIED:
        return <XCircle className="h-5 w-5 text-red-500" />
      case PermissionStatus.NOT_DETERMINED:
        return <AlertCircle className="h-5 w-5 text-yellow-500" />
      case PermissionStatus.RESTRICTED:
        return <XCircle className="h-5 w-5 text-gray-400" />
      default:
        return <AlertCircle className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusText = () => {
    switch (permission.status) {
      case PermissionStatus.GRANTED:
        return t('permissions.status.granted')
      case PermissionStatus.DENIED:
        return t('permissions.status.denied')
      case PermissionStatus.NOT_DETERMINED:
        return t('permissions.status.notDetermined')
      case PermissionStatus.RESTRICTED:
        return t('permissions.status.restricted')
      default:
        return t('permissions.status.unknown')
    }
  }

  const getStatusColor = () => {
    switch (permission.status) {
      case PermissionStatus.GRANTED:
        return 'text-green-600 dark:text-green-400'
      case PermissionStatus.DENIED:
        return 'text-red-600 dark:text-red-400'
      case PermissionStatus.NOT_DETERMINED:
        return 'text-yellow-600 dark:text-yellow-400'
      case PermissionStatus.RESTRICTED:
        return 'text-gray-500'
      default:
        return 'text-gray-500'
    }
  }

  const needsAction = permission.status !== PermissionStatus.GRANTED

  return (
    <div className="bg-card rounded-lg border p-4 transition-all hover:shadow-sm">
      <div className="flex items-start gap-4">
        <div className="mt-0.5">{getStatusIcon()}</div>

        <div className="flex-1 space-y-2">
          <div>
            <h3 className="text-base font-semibold">{permission.name}</h3>
            <p className="text-muted-foreground mt-1 text-sm">{permission.description}</p>
          </div>

          <div className="flex items-center justify-between">
            <span className={`text-sm font-medium ${getStatusColor()}`}>{getStatusText()}</span>

            {needsAction && (
              <Button size="sm" variant="outline" onClick={() => onOpenSettings(permission.type)} className="gap-2">
                <ExternalLink className="h-3.5 w-3.5" />
                {t('permissions.openSettings')}
              </Button>
            )}
          </div>

          {needsAction && permission.systemSettingsPath && (
            <div className="text-muted-foreground bg-muted/50 rounded-md p-2 text-xs">
              <span className="font-medium">{t('permissions.settingsPath')}:</span> {permission.systemSettingsPath}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
