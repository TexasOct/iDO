/**
 * Permission management service layer
 */

import * as apiClient from '@/lib/client/apiClient'
import type { PermissionsCheckResponse, OpenSystemSettingsRequest, RestartAppRequest } from '@/lib/types/permissions'

/**
 * Check all required system permissions
 */
export async function checkPermissions(): Promise<PermissionsCheckResponse> {
  try {
    const response = await apiClient.checkPermissions(null)
    // Backend returns a plain object; convert the type
    return response as unknown as PermissionsCheckResponse
  } catch (error) {
    console.error('Failed to check permissions:', error)
    throw error
  }
}

/**
 * Open the system settings page for the permission
 */
export async function openSystemSettings(
  request: OpenSystemSettingsRequest
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await apiClient.openSystemSettings(request)
    return response as { success: boolean; message: string }
  } catch (error) {
    console.error('Failed to open system settings:', error)
    throw error
  }
}

/**
 * Request accessibility permission
 */
export async function requestAccessibilityPermission(): Promise<{
  success: boolean
  granted: boolean
  message: string
}> {
  try {
    const response = await apiClient.requestAccessibilityPermission(null)
    return response as { success: boolean; granted: boolean; message: string }
  } catch (error) {
    console.error('Failed to request accessibility permission:', error)
    throw error
  }
}

/**
 * Restart the app
 */
export async function restartApp(request?: RestartAppRequest): Promise<{ success: boolean; message: string }> {
  try {
    const response = await apiClient.restartApp(request || { delaySeconds: 1 })
    return response as { success: boolean; message: string }
  } catch (error) {
    console.error('Failed to restart the app:', error)
    throw error
  }
}
