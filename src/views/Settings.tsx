import { useTranslation } from 'react-i18next'
import ModelManagement from '@/components/models/ModelManagement'
import { Live2dSettings } from '@/components/settings/Live2dSettings'
import { FriendlyChatSettings } from '@/components/settings/FriendlyChatSettings'
import { GeneralSettings } from '@/components/settings/GeneralSettings'
import { DatabaseSettings } from '@/components/settings/DatabaseSettings'
import { ScreenshotSettings } from '@/components/settings/ScreenshotSettings'
import { ScreenSelectionSettings } from '@/components/settings/ScreenSelectionSettings'
import { AppearanceSettings } from '@/components/settings/AppearanceSettings'
import { PermissionsSettings } from '@/components/settings/PermissionsSettings'

export default function SettingsView() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex-shrink-0 border-b px-6 py-4">
        <h1 className="text-2xl font-semibold">{t('settings.title')}</h1>
        <p className="text-muted-foreground mt-1 text-sm">{t('settings.description')}</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl space-y-6">
          {/* 模型管理 */}
          <ModelManagement />

          {/* Live2D 设置 */}
          <Live2dSettings />

          {/* 友好聊天设置 */}
          <FriendlyChatSettings />

          {/* 通用设置 */}
          <GeneralSettings />

          {/* 数据库设置 */}
          <DatabaseSettings />

          {/* 截屏设置 */}
          <ScreenshotSettings />

          {/* 屏幕选择设置 */}
          <ScreenSelectionSettings />

          {/* 外观设置 */}
          <AppearanceSettings />

          {/* 系统权限管理 */}
          <PermissionsSettings />
        </div>
      </div>
    </div>
  )
}
