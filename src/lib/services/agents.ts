/**
 * Agent服务层
 * 连接前端和后端Agent API
 */

import * as apiClient from '@/lib/client/apiClient'
import type { CreateTaskRequest, ExecuteTaskRequest, DeleteTaskRequest, GetTasksRequest } from '@/lib/client/_apiTypes'
import { AgentTask, AgentConfig } from '@/lib/types/agents'

/**
 * 创建新的Agent任务
 */
export async function createTask(request: CreateTaskRequest): Promise<AgentTask> {
  try {
    const response = await apiClient.createTask(request as any)

    if ((response as any).success && (response as any).data) {
      return (response as any).data as AgentTask
    } else {
      throw new Error((response as any).message || '创建任务失败')
    }
  } catch (error) {
    console.error('创建任务失败:', error)
    throw error
  }
}

/**
 * 执行Agent任务
 */
export async function executeTask(request: ExecuteTaskRequest): Promise<void> {
  try {
    const response = await apiClient.executeTask(request as any)

    if (!(response as any).success) {
      throw new Error((response as any).message || '执行任务失败')
    }
  } catch (error) {
    console.error('执行任务失败:', error)
    throw error
  }
}

/**
 * 删除Agent任务
 */
export async function deleteTask(request: DeleteTaskRequest): Promise<void> {
  try {
    const response = await apiClient.deleteTask(request as any)

    if (!(response as any).success) {
      throw new Error((response as any).message || '删除任务失败')
    }
  } catch (error) {
    console.error('删除任务失败:', error)
    throw error
  }
}

/**
 * 获取Agent任务列表
 */
export async function getTasks(request?: GetTasksRequest): Promise<AgentTask[]> {
  try {
    const response = await apiClient.getTasks(request as any)

    if ((response as any).success && (response as any).data) {
      return (response as any).data as AgentTask[]
    } else {
      throw new Error((response as any).message || '获取任务列表失败')
    }
  } catch (error) {
    console.error('获取任务列表失败:', error)
    throw error
  }
}

/**
 * 获取可用的Agent列表
 */
export async function getAvailableAgents(): Promise<AgentConfig[]> {
  try {
    const response = await apiClient.getAvailableAgents({} as any)

    if ((response as any).success && (response as any).data) {
      return (response as any).data as AgentConfig[]
    } else {
      throw new Error((response as any).message || '获取可用Agent列表失败')
    }
  } catch (error) {
    console.error('获取可用Agent列表失败:', error)
    throw error
  }
}

/**
 * 获取任务状态
 */
export async function getTaskStatus(request: ExecuteTaskRequest): Promise<AgentTask> {
  try {
    const response = await apiClient.getTaskStatus(request as any)

    if ((response as any).success && (response as any).data) {
      return (response as any).data as AgentTask
    } else {
      throw new Error((response as any).message || '获取任务状态失败')
    }
  } catch (error) {
    console.error('获取任务状态失败:', error)
    throw error
  }
}
