/**
 * Event bus built on mitt for global communication
 * Used to decouple communication between components
 */

import mitt from 'mitt'

// Define event types
export type TodoToChatEvent = {
  todoId: string
  title: string
  description?: string
  keywords: string[]
  createdAt?: string
}

// Activity record event types
export type ActivityToChatEvent = {
  activityId: string
  title: string
  description?: string
  screenshots?: string[]
  keywords: string[]
  timestamp: number
}

// Recent event types (with screenshots)
export type EventToChatEvent = {
  eventId: string
  summary: string
  description?: string
  screenshots: string[] // Required array
  keywords: string[]
  timestamp: number
}

// Knowledge organization event types
export type KnowledgeToChatEvent = {
  knowledgeId: string
  title: string
  description: string
  keywords: string[]
  createdAt: number
}

// Combine all event types
export type EventMap = {
  'todo:execute-in-chat': TodoToChatEvent
  'activity:send-to-chat': ActivityToChatEvent
  'event:send-to-chat': EventToChatEvent
  'knowledge:send-to-chat': KnowledgeToChatEvent
  // Additional event types can be added later
  // 'user:logout': void
  // 'notification:show': { message: string; type?: 'info' | 'success' | 'error' }
}

// Create the event bus instance
export const eventBus = mitt<EventMap>()

// Debug logging
eventBus.on('*', (type, event) => {
  console.log(`[EventBus] Event emitted: ${type}`, event)
})

// Export helpers for convenience

// Todo-related
export const emitTodoToChat = (data: TodoToChatEvent) => {
  eventBus.emit('todo:execute-in-chat', data)
}

export const onTodoToChat = (handler: (data: TodoToChatEvent) => void) => {
  eventBus.on('todo:execute-in-chat', handler)
  return () => eventBus.off('todo:execute-in-chat', handler)
}

// Activity-related
export const emitActivityToChat = (data: ActivityToChatEvent) => {
  eventBus.emit('activity:send-to-chat', data)
}

export const onActivityToChat = (handler: (data: ActivityToChatEvent) => void) => {
  eventBus.on('activity:send-to-chat', handler)
  return () => eventBus.off('activity:send-to-chat', handler)
}

// Recent events
export const emitEventToChat = (data: EventToChatEvent) => {
  eventBus.emit('event:send-to-chat', data)
}

export const onEventToChat = (handler: (data: EventToChatEvent) => void) => {
  eventBus.on('event:send-to-chat', handler)
  return () => eventBus.off('event:send-to-chat', handler)
}

// Knowledge organization
export const emitKnowledgeToChat = (data: KnowledgeToChatEvent) => {
  eventBus.emit('knowledge:send-to-chat', data)
}

export const onKnowledgeToChat = (handler: (data: KnowledgeToChatEvent) => void) => {
  eventBus.on('knowledge:send-to-chat', handler)
  return () => eventBus.off('knowledge:send-to-chat', handler)
}
