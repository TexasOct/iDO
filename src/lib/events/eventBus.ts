/**
 * 事件总线 - 使用 mitt 实现全局事件通信
 * 用于解耦组件间的通信
 */

import mitt from 'mitt'

// 定义事件类型
export type TodoToChatEvent = {
  todoId: string
  title: string
  description?: string
  keywords: string[]
  createdAt?: string
}

// 活动记录事件类型
export type ActivityToChatEvent = {
  activityId: string
  title: string
  description?: string
  screenshots?: string[]
  keywords: string[]
  timestamp: number
}

// 最近事件类型（包含截图）
export type EventToChatEvent = {
  eventId: string
  summary: string
  description?: string
  screenshots: string[] // 改为必需数组
  keywords: string[]
  timestamp: number
}

// 知识整理类型
export type KnowledgeToChatEvent = {
  knowledgeId: string
  title: string
  description: string
  keywords: string[]
  createdAt: number
}

// 合并所有事件类型
export type EventMap = {
  'todo:execute-in-chat': TodoToChatEvent
  'activity:send-to-chat': ActivityToChatEvent
  'event:send-to-chat': EventToChatEvent
  'knowledge:send-to-chat': KnowledgeToChatEvent
  // 未来可以添加更多事件类型
  // 'user:logout': void
  // 'notification:show': { message: string; type?: 'info' | 'success' | 'error' }
}

// 创建事件总线实例
export const eventBus = mitt<EventMap>()

// 添加调试日志
eventBus.on('*', (type, event) => {
  console.log(`[EventBus] 事件触发: ${type}`, event)
})

// 为了方便使用，也可以导出常用方法

// 待办相关
export const emitTodoToChat = (data: TodoToChatEvent) => {
  eventBus.emit('todo:execute-in-chat', data)
}

export const onTodoToChat = (handler: (data: TodoToChatEvent) => void) => {
  eventBus.on('todo:execute-in-chat', handler)
  return () => eventBus.off('todo:execute-in-chat', handler)
}

// 活动记录相关
export const emitActivityToChat = (data: ActivityToChatEvent) => {
  eventBus.emit('activity:send-to-chat', data)
}

export const onActivityToChat = (handler: (data: ActivityToChatEvent) => void) => {
  eventBus.on('activity:send-to-chat', handler)
  return () => eventBus.off('activity:send-to-chat', handler)
}

// 最近事件相关
export const emitEventToChat = (data: EventToChatEvent) => {
  eventBus.emit('event:send-to-chat', data)
}

export const onEventToChat = (handler: (data: EventToChatEvent) => void) => {
  eventBus.on('event:send-to-chat', handler)
  return () => eventBus.off('event:send-to-chat', handler)
}

// 知识整理相关
export const emitKnowledgeToChat = (data: KnowledgeToChatEvent) => {
  eventBus.emit('knowledge:send-to-chat', data)
}

export const onKnowledgeToChat = (handler: (data: KnowledgeToChatEvent) => void) => {
  eventBus.on('knowledge:send-to-chat', handler)
  return () => eventBus.off('knowledge:send-to-chat', handler)
}
