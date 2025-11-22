/**
 * Chat 服务层
 * 连接前端和后端 Chat API
 */

import * as apiClient from '@/lib/client/apiClient'
import type { Conversation, Message } from '@/lib/types/chat'

/**
 * 创建新对话
 */
export async function createConversation(params: {
  title: string
  relatedActivityIds?: string[]
  metadata?: Record<string, any>
  modelId?: string | null
}): Promise<Conversation> {
  try {
    const response = await apiClient.createConversation({
      title: params.title,
      relatedActivityIds: params.relatedActivityIds,
      metadata: params.metadata,
      modelId: params.modelId
    } as any)

    if ((response as any).success && (response as any).data) {
      return (response as any).data as Conversation
    } else {
      throw new Error((response as any).message || '创建对话失败')
    }
  } catch (error) {
    console.error('创建对话失败:', error)
    throw error
  }
}

/**
 * 从活动创建对话
 */
export async function createConversationFromActivities(activityIds: string[]): Promise<{
  conversationId: string
  title: string
  context: string
}> {
  try {
    const response = await apiClient.createConversationFromActivities({
      activityIds
    } as any)

    if ((response as any).success && (response as any).data) {
      return (response as any).data
    } else {
      throw new Error((response as any).message || '从活动创建对话失败')
    }
  } catch (error) {
    console.error('从活动创建对话失败:', error)
    throw error
  }
}

/**
 * 发送消息（流式输出）
 * 注意：实际的消息内容通过 Tauri Events 接收
 * 支持多模态消息（文本+图片）
 */
export async function sendMessage(
  conversationId: string,
  content: string,
  images?: string[],
  modelId?: string | null
): Promise<void> {
  try {
    const response = await apiClient.sendMessage({
      conversationId,
      content,
      images,
      model_id: modelId
    } as any)

    if (!(response as any).success) {
      throw new Error((response as any).message || '发送消息失败')
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    throw error
  }
}

/**
 * 获取对话列表
 */
export async function getConversations(params?: { limit?: number; offset?: number }): Promise<Conversation[]> {
  try {
    const response = await apiClient.getConversations({
      limit: params?.limit,
      offset: params?.offset
    } as any)

    if ((response as any).success && (response as any).data) {
      return (response as any).data as Conversation[]
    } else {
      throw new Error((response as any).message || '获取对话列表失败')
    }
  } catch (error) {
    console.error('获取对话列表失败:', error)
    throw error
  }
}

/**
 * 获取消息列表
 */
export async function getMessages(params: {
  conversationId: string
  limit?: number
  offset?: number
}): Promise<Message[]> {
  try {
    const response = await apiClient.getMessages({
      conversationId: params.conversationId,
      limit: params.limit,
      offset: params.offset
    } as any)

    if ((response as any).success && (response as any).data) {
      return (response as any).data as Message[]
    } else {
      throw new Error((response as any).message || '获取消息列表失败')
    }
  } catch (error) {
    console.error('获取消息列表失败:', error)
    throw error
  }
}

/**
 * 删除对话
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  try {
    const response = await apiClient.deleteConversation({
      conversationId
    } as any)

    if (!(response as any).success) {
      throw new Error((response as any).message || '删除对话失败')
    }
  } catch (error) {
    console.error('删除对话失败:', error)
    throw error
  }
}
