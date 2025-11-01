import { create } from 'zustand'
import {
  deleteDiary,
  deleteKnowledge,
  deleteTodo,
  fetchDiaryList,
  fetchKnowledgeList,
  fetchRecentEvents,
  fetchTodoList,
  generateDiary,
  InsightDiary,
  InsightEvent,
  InsightKnowledge,
  InsightTodo
} from '@/lib/services/insights'

interface InsightsState {
  recentEvents: InsightEvent[]
  knowledge: InsightKnowledge[]
  todos: InsightTodo[]
  diaries: InsightDiary[]

  recentEventsLimit: number
  todoIncludeCompleted: boolean

  loadingEvents: boolean
  loadingKnowledge: boolean
  loadingTodos: boolean
  loadingDiaries: boolean
  lastError?: string

  fetchRecentEvents: (limit?: number) => Promise<void>
  refreshKnowledge: () => Promise<void>
  refreshTodos: (includeCompleted?: boolean) => Promise<void>
  refreshDiaries: (limit?: number) => Promise<void>

  removeKnowledge: (id: string) => Promise<void>
  removeTodo: (id: string) => Promise<void>
  removeDiary: (id: string) => Promise<void>

  createDiaryForDate: (date: string) => Promise<InsightDiary>
  clearError: () => void
  setRecentEventsLimit: (limit: number) => void
}

const DEFAULT_EVENT_LIMIT = 5

export const useInsightsStore = create<InsightsState>((set, get) => ({
  recentEvents: [],
  knowledge: [],
  todos: [],
  diaries: [],

  recentEventsLimit: DEFAULT_EVENT_LIMIT,
  todoIncludeCompleted: false,

  loadingEvents: false,
  loadingKnowledge: false,
  loadingTodos: false,
  loadingDiaries: false,
  lastError: undefined,

  fetchRecentEvents: async (limit) => {
    const finalLimit = limit ?? get().recentEventsLimit
    set({ loadingEvents: true, recentEventsLimit: finalLimit, lastError: undefined })
    try {
      const events = await fetchRecentEvents(finalLimit)
      set({ recentEvents: events })
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : String(error) })
    } finally {
      set({ loadingEvents: false })
    }
  },

  refreshKnowledge: async () => {
    set({ loadingKnowledge: true, lastError: undefined })
    try {
      const knowledge = await fetchKnowledgeList()
      set({ knowledge })
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : String(error) })
    } finally {
      set({ loadingKnowledge: false })
    }
  },

  refreshTodos: async (includeCompleted) => {
    const finalInclude = includeCompleted ?? get().todoIncludeCompleted
    set({ loadingTodos: true, todoIncludeCompleted: finalInclude, lastError: undefined })
    try {
      const todos = await fetchTodoList(finalInclude)
      set({ todos })
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : String(error) })
    } finally {
      set({ loadingTodos: false })
    }
  },

  refreshDiaries: async (limit = 10) => {
    set({ loadingDiaries: true, lastError: undefined })
    try {
      const diaries = await fetchDiaryList(limit)
      set({ diaries })
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : String(error) })
    } finally {
      set({ loadingDiaries: false })
    }
  },

  removeKnowledge: async (id: string) => {
    await deleteKnowledge(id)
    set((state) => ({ knowledge: state.knowledge.filter((item) => item.id !== id) }))
  },

  removeTodo: async (id: string) => {
    await deleteTodo(id)
    set((state) => ({ todos: state.todos.filter((item) => item.id !== id) }))
  },

  removeDiary: async (id: string) => {
    await deleteDiary(id)
    set((state) => ({ diaries: state.diaries.filter((item) => item.id !== id) }))
  },

  createDiaryForDate: async (date: string) => {
    const diary = await generateDiary(date)
    set((state) => ({ diaries: [diary, ...state.diaries.filter((item) => item.id !== diary.id)] }))
    return diary
  },

  clearError: () => set({ lastError: undefined }),

  setRecentEventsLimit: (limit: number) => {
    set({ recentEventsLimit: Math.max(1, limit) })
  }
}))
