/**
 * 权限管理服务层
 */

import * as apiClient from '@/lib/client/apiClient'
import type { PermissionsCheckResponse, OpenSystemSettingsRequest, RestartAppRequest } from '@/lib/types/permissions'

/**
 * 检查所有必需的系统权限
 */
export async function checkPermissions(): Promise<PermissionsCheckResponse> {
  try {
    const response = await apiClient.checkPermissions(null)
    return response as PermissionsCheckResponse
  } catch (error) {
    console.error('检查权限失败:', error)
    throw error
  }
}

/**
 * 打开系统设置对应的权限页面
 */
export async function openSystemSettings(
  request: OpenSystemSettingsRequest
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await apiClient.openSystemSettings(request)
    return response as { success: boolean; message: string }
  } catch (error) {
    console.error('打开系统设置失败:', error)
    throw error
  }
}

/**
 * 请求辅助功能权限
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
    console.error('请求辅助功能权限失败:', error)
    throw error
  }
}

/**
 * 重启应用
 */
export async function restartApp(request?: RestartAppRequest): Promise<{ success: boolean; message: string }> {
  try {
    const response = await apiClient.restartApp(request || { delaySeconds: 1 })
    return response as { success: boolean; message: string }
  } catch (error) {
    console.error('重启应用失败:', error)
    throw error
  }
}
