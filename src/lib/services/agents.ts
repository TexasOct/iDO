/**
 * Agent服务层
 * 连接前端和后端Agent API
 */

import * as apiClient from '@/lib/client/apiClient'
import { AgentTask, AgentConfig } from '@/lib/types/agents'

export interface CreateTaskRequest {
  agent: string
  planDescription: string
}

export interface ExecuteTaskRequest {
  taskId: string
}

export interface DeleteTaskRequest {
  taskId: string
}

export interface GetTasksRequest {
  limit?: number
  status?: string
}

export interface GetAvailableAgentsRequest {
  // 空请求体
}

/**
 * 创建新的Agent任务
 */
export async function createTask(request: CreateTaskRequest): Promise<AgentTask> {
  try {
    const response = await apiClient.createTask(request)
    
    if (response.success && response.data) {
      return response.data as AgentTask
    } else {
      throw new Error(response.message || '创建任务失败')
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
    const response = await apiClient.executeTask(request)
    
    if (!response.success) {
      throw new Error(response.message || '执行任务失败')
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
    const response = await apiClient.deleteTask(request)
    
    if (!response.success) {
      throw new Error(response.message || '删除任务失败')
    }
  } catch (error) {
    console.error('删除任务失败:', error)
    throw error
  }
}

/**
 * 获取Agent任务列表
 */
export async function getTasks(request: GetTasksRequest = {}): Promise<AgentTask[]> {
  try {
    const response = await apiClient.getTasks(request)
    
    if (response.success && response.data) {
      return response.data as AgentTask[]
    } else {
      throw new Error(response.message || '获取任务列表失败')
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
    const response = await apiClient.getAvailableAgents({})
    
    if (response.success && response.data) {
      return response.data as AgentConfig[]
    } else {
      throw new Error(response.message || '获取可用Agent列表失败')
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
    const response = await apiClient.getTaskStatus(request)
    
    if (response.success && response.data) {
      return response.data as AgentTask
    } else {
      throw new Error(response.message || '获取任务状态失败')
    }
  } catch (error) {
    console.error('获取任务状态失败:', error)
    throw error
  }
}
