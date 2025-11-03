/**
 * 权限相关的类型定义
 */

export enum PermissionType {
  ACCESSIBILITY = 'accessibility',
  SCREEN_RECORDING = 'screen_recording'
}

export enum PermissionStatus {
  GRANTED = 'granted',
  DENIED = 'denied',
  NOT_DETERMINED = 'not_determined',
  RESTRICTED = 'restricted'
}

export interface PermissionInfo {
  type: PermissionType
  status: PermissionStatus
  name: string
  description: string
  required: boolean
  systemSettingsPath: string
}

export interface PermissionsCheckResponse {
  allGranted: boolean
  permissions: Record<string, PermissionInfo>
  platform: string
  needsRestart: boolean
}

export interface OpenSystemSettingsRequest {
  permissionType: PermissionType
}

export interface RestartAppRequest {
  delaySeconds?: number
}
