/**
 * 权限状态管理 Store
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { PermissionsCheckResponse } from '@/lib/types/permissions'
import * as permissionsService from '@/lib/services/permissions'

interface PermissionsState {
  // 状态
  permissionsData: PermissionsCheckResponse | null
  loading: boolean
  error: string | null
  hasChecked: boolean // 是否已经检查过权限
  userDismissed: boolean // 用户是否主动关闭了引导

  // Actions
  checkPermissions: () => Promise<void>
  openSystemSettings: (permissionType: string) => Promise<void>
  requestAccessibility: () => Promise<void>
  restartApp: () => Promise<void>
  dismissGuide: () => void
  reset: () => void
}

export const usePermissionsStore = create<PermissionsState>()(
  persist(
    (set, get) => ({
      permissionsData: null,
      loading: false,
      error: null,
      hasChecked: false,
      userDismissed: false,

      checkPermissions: async () => {
        set({ loading: true, error: null })
        try {
          const data = await permissionsService.checkPermissions()
          console.log('🔍 权限检查 - 收到后端数据:', data)
          console.log('🔍 allGranted 值:', data.allGranted, '类型:', typeof data.allGranted)
          set({
            permissionsData: data,
            loading: false,
            hasChecked: true,
            error: null
          })
          console.log('✅ 权限数据已更新到 store')
        } catch (error) {
          console.error('检查权限失败:', error)
          set({
            error: (error as Error).message,
            loading: false
          })
        }
      },

      openSystemSettings: async (permissionType: string) => {
        try {
          await permissionsService.openSystemSettings({
            permissionType: permissionType as any
          })
        } catch (error) {
          console.error('打开系统设置失败:', error)
          throw error
        }
      },

      requestAccessibility: async () => {
        try {
          const result = await permissionsService.requestAccessibilityPermission()
          console.log('请求辅助功能权限结果:', result)

          // 重新检查权限
          await get().checkPermissions()
        } catch (error) {
          console.error('请求辅助功能权限失败:', error)
          throw error
        }
      },

      restartApp: async () => {
        try {
          await permissionsService.restartApp({ delaySeconds: 1 })
        } catch (error) {
          console.error('重启应用失败:', error)
          throw error
        }
      },

      dismissGuide: () => {
        set({ userDismissed: true })
      },

      reset: () => {
        set({
          permissionsData: null,
          loading: false,
          error: null,
          hasChecked: false,
          userDismissed: false
        })
      }
    }),
    {
      name: 'ido-permissions',
      partialize: (state) => ({
        // 只持久化用户主动关闭的状态
        userDismissed: state.userDismissed
      })
    }
  )
)
