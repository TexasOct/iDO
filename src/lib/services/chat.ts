/**
 * Chat service layer
 * Connects the frontend with backend Chat APIs
 */

import * as apiClient from '@/lib/client/apiClient'
import type { Conversation, Message } from '@/lib/types/chat'

/**
 * Create a new conversation
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
      throw new Error((response as any).message || 'Failed to create conversation')
    }
  } catch (error) {
    console.error('Failed to create conversation:', error)
    throw error
  }
}

/**
 * Create a conversation from an activity
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
      throw new Error((response as any).message || 'Failed to create conversation from activity')
    }
  } catch (error) {
    console.error('Failed to create conversation from activity:', error)
    throw error
  }
}

/**
 * Send a message (streamed output)
 * Note: actual message content arrives via Tauri events
 * Supports multimodal messages (text + images)
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
      throw new Error((response as any).message || 'Failed to send message')
    }
  } catch (error) {
    console.error('Failed to send message:', error)
    throw error
  }
}

/**
 * Fetch the conversation list
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
      throw new Error((response as any).message || 'Failed to fetch conversation list')
    }
  } catch (error) {
    console.error('Failed to fetch conversation list:', error)
    throw error
  }
}

/**
 * Fetch the message list
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
      throw new Error((response as any).message || 'Failed to fetch message list')
    }
  } catch (error) {
    console.error('Failed to fetch message list:', error)
    throw error
  }
}

/**
 * Delete a conversation
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  try {
    const response = await apiClient.deleteConversation({
      conversationId
    } as any)

    if (!(response as any).success) {
      throw new Error((response as any).message || 'Failed to delete conversation')
    }
  } catch (error) {
    console.error('Failed to delete conversation:', error)
    throw error
  }
}
