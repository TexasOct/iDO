/**
 * Permission state store
 */

import { create } from 'zustand'
import type { PermissionsCheckResponse } from '@/lib/types/permissions'
import * as permissionsService from '@/lib/services/permissions'

interface PermissionsState {
  // State
  permissionsData: PermissionsCheckResponse | null
  loading: boolean
  error: string | null
  hasChecked: boolean // Whether a permission check already ran
  userDismissed: boolean // Whether the user dismissed the guide
  pendingRestart: boolean // Whether a restart has been requested to apply permission changes

  // Actions
  checkPermissions: () => Promise<void>
  openSystemSettings: (permissionType: string) => Promise<void>
  requestAccessibility: () => Promise<void>
  restartApp: () => Promise<void>
  dismissGuide: () => void
  // Allow external code to set pendingRestart (for tests or manual cleanup)
  setPendingRestart: (value: boolean) => void
  reset: () => void
}

export const usePermissionsStore = create<PermissionsState>()((set, get) => ({
  permissionsData: null,
  loading: false,
  error: null,
  hasChecked: false,
  userDismissed: false,
  pendingRestart: false,

  checkPermissions: async () => {
    set({ loading: true, error: null })
    try {
      const data = await permissionsService.checkPermissions()
      console.log('🔍 Permission check - backend data:', data)
      console.log('🔍 allGranted value:', data.allGranted, 'type:', typeof data.allGranted)
      set({
        permissionsData: data,
        loading: false,
        hasChecked: true,
        error: null,
        // Clear pendingRestart when all permissions are granted (after restart/manual completion)
        // Otherwise rely on the backend needsRestart flag
        pendingRestart: data?.allGranted ? false : !!data.needsRestart
      })
      console.log('✅ Permission data updated in store')
    } catch (error) {
      console.error('Failed to check permissions:', error)
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
      console.error('Failed to open system settings:', error)
      throw error
    }
  },

  requestAccessibility: async () => {
    try {
      const result = await permissionsService.requestAccessibilityPermission()
      console.log('Accessibility permission request result:', result)

      // Re-run the permission check
      await get().checkPermissions()
    } catch (error) {
      console.error('Failed to request accessibility permissions:', error)
      throw error
    }
  },

  restartApp: async () => {
    try {
      // Ask the backend to restart the app
      await permissionsService.restartApp({ delaySeconds: 1 })
      // Mark pendingRestart so the UI can persist the reboot hint
      set({ pendingRestart: true })
    } catch (error) {
      console.error('Failed to restart the app:', error)
      throw error
    }
  },

  dismissGuide: () => {
    set({ userDismissed: true })
  },

  // Explicitly set pendingRestart (testing/external control)
  setPendingRestart: (value: boolean) => {
    set({ pendingRestart: value })
  },

  reset: () => {
    set({
      permissionsData: null,
      loading: false,
      error: null,
      hasChecked: false,
      userDismissed: false,
      pendingRestart: false
    })
  }
}))
