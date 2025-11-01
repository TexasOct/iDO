import {
  getRecentEvents,
  getKnowledgeList,
  deleteKnowledge as deleteKnowledgeCommand,
  getTodoList,
  deleteTodo as deleteTodoCommand,
  generateDiary as generateDiaryCommand,
  deleteDiary as deleteDiaryCommand,
  getPipelineStats,
  getDiaryList
} from '@/lib/client/apiClient'

export interface InsightEvent {
  id: string
  title: string
  description: string
  keywords: string[]
  timestamp?: string
  createdAt?: string
}

export interface InsightKnowledge {
  id: string
  title: string
  description: string
  keywords: string[]
  mergedFromIds?: string[]
  createdAt?: string
  type?: 'combined' | 'original'
  deleted?: boolean
}

export interface InsightTodo {
  id: string
  title: string
  description: string
  keywords: string[]
  mergedFromIds?: string[]
  createdAt?: string
  completed?: boolean
  deleted?: boolean
  type?: 'combined' | 'original'
}

export interface InsightDiary {
  id: string
  date: string
  content: string
  sourceActivityIds: string[]
  createdAt?: string
}

interface ApiResponse<T> {
  success?: boolean
  message?: string
  data?: T
}

const ensureSuccess = <T>(response: ApiResponse<T>): T => {
  if (!response?.success) {
    throw new Error(response?.message ?? 'Unknown backend error')
  }
  if (!response.data) {
    throw new Error('Backend returned empty data')
  }
  return response.data
}

export async function fetchRecentEvents(limit: number): Promise<InsightEvent[]> {
  const raw = await getRecentEvents({ limit })
  const data = ensureSuccess<{ events?: any[] }>(raw)
  const events = Array.isArray(data.events) ? data.events : []
  return events.map((event) => ({
    id: String(event.id ?? ''),
    title: String(event.title ?? ''),
    description: String(event.description ?? ''),
    keywords: Array.isArray(event.keywords) ? event.keywords : [],
    timestamp: typeof event.timestamp === 'string' ? event.timestamp : undefined,
    createdAt: typeof event.created_at === 'string' ? event.created_at : undefined
  }))
}

export async function fetchKnowledgeList(): Promise<InsightKnowledge[]> {
  const raw = await getKnowledgeList()
  const data = ensureSuccess<{ knowledge?: any[] }>(raw)
  const knowledge = Array.isArray(data.knowledge) ? data.knowledge : []
  return knowledge.map((item) => ({
    id: String(item.id ?? ''),
    title: String(item.title ?? ''),
    description: String(item.description ?? ''),
    keywords: Array.isArray(item.keywords) ? item.keywords : [],
    mergedFromIds: Array.isArray(item.merged_from_ids) ? item.merged_from_ids : [],
    createdAt: typeof item.created_at === 'string' ? item.created_at : undefined,
    type: item.type === 'combined' ? 'combined' : 'original',
    deleted: Boolean(item.deleted)
  }))
}

export async function deleteKnowledge(id: string) {
  const raw = await deleteKnowledgeCommand({ id })
  if (!raw?.success) {
    throw new Error(raw?.message ?? 'Failed to delete knowledge')
  }
}

export async function fetchTodoList(includeCompleted = false): Promise<InsightTodo[]> {
  const raw = await getTodoList({ includeCompleted })
  const data = ensureSuccess<{ todos?: any[] }>(raw)
  const todos = Array.isArray(data.todos) ? data.todos : []
  return todos.map((todo) => ({
    id: String(todo.id ?? ''),
    title: String(todo.title ?? ''),
    description: String(todo.description ?? ''),
    keywords: Array.isArray(todo.keywords) ? todo.keywords : [],
    mergedFromIds: Array.isArray(todo.merged_from_ids) ? todo.merged_from_ids : [],
    createdAt: typeof todo.created_at === 'string' ? todo.created_at : undefined,
    completed: Boolean(todo.completed),
    deleted: Boolean(todo.deleted),
    type: todo.type === 'combined' ? 'combined' : 'original'
  }))
}

export async function deleteTodo(id: string) {
  const raw = await deleteTodoCommand({ id })
  if (!raw?.success) {
    throw new Error(raw?.message ?? 'Failed to delete todo')
  }
}

export async function generateDiary(date: string): Promise<InsightDiary> {
  const raw = await generateDiaryCommand({ date })
  const data = ensureSuccess<any>(raw)
  return {
    id: String(data.id ?? ''),
    date: String(data.date ?? ''),
    content: String(data.content ?? ''),
    sourceActivityIds: Array.isArray(data.source_activity_ids) ? data.source_activity_ids : [],
    createdAt: typeof data.created_at === 'string' ? data.created_at : undefined
  }
}

export async function fetchDiaryList(limit: number): Promise<InsightDiary[]> {
  const raw = await getDiaryList({ limit })
  const data = ensureSuccess<{ diaries?: any[] }>(raw)
  const diaries = Array.isArray(data.diaries) ? data.diaries : []
  return diaries.map((diary) => ({
    id: String(diary.id ?? ''),
    date: String(diary.date ?? ''),
    content: String(diary.content ?? ''),
    sourceActivityIds: Array.isArray(diary.source_activity_ids) ? diary.source_activity_ids : [],
    createdAt: typeof diary.created_at === 'string' ? diary.created_at : undefined
  }))
}

export async function deleteDiary(id: string) {
  const raw = await deleteDiaryCommand({ id })
  if (!raw?.success) {
    throw new Error(raw?.message ?? 'Failed to delete diary')
  }
}

export async function fetchPipelineStats() {
  const raw = await getPipelineStats()
  return ensureSuccess(raw)
}
