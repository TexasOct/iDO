import { create } from 'zustand'
import { AgentTask, AgentType, AgentConfig, TaskStatus } from '@/lib/types/agents'
import * as agentService from '@/lib/services/agents'

interface AgentsState {
  tasks: AgentTask[]
  availableAgents: AgentConfig[]
  selectedAgent: AgentType | null
  planDescription: string
  loading: boolean
  error: string | null

  // Actions
  fetchTasks: () => Promise<void>
  fetchAvailableAgents: () => Promise<void>
  createTask: (agent: AgentType, plan: string) => Promise<void>
  executeTask: (taskId: string) => Promise<void>
  stopTask: (taskId: string) => Promise<void>
  deleteTask: (taskId: string) => Promise<void>
  updateTaskStatus: (taskId: string, updates: Partial<AgentTask>) => void
  setSelectedAgent: (agent: AgentType | null) => void
  setPlanDescription: (description: string) => void

  // Computed
  getTodoTasks: () => AgentTask[]
  getProcessingTasks: () => AgentTask[]
  getDoneTasks: () => AgentTask[]
}

export const useAgentsStore = create<AgentsState>((set, get) => ({
  tasks: [],
  availableAgents: [
    { name: 'SimpleAgent', description: '通用智能助手，使用smolagents库处理各种任务' },
    { name: 'WritingAgent', description: '写作助手，帮助撰写文档和文章' },
    { name: 'ResearchAgent', description: '研究助手，帮助收集和整理资料' },
    { name: 'AnalysisAgent', description: '分析助手，帮助数据分析和总结' }
  ],
  selectedAgent: null,
  planDescription: '',
  loading: false,
  error: null,

  fetchTasks: async () => {
    set({ loading: true, error: null })
    try {
      const tasks = await agentService.getTasks({ limit: 50 })
      set({ tasks, loading: false })
    } catch (error) {
      set({ error: (error as Error).message, loading: false })
    }
  },

  fetchAvailableAgents: async () => {
    try {
      const agents = await agentService.getAvailableAgents()
      set({ availableAgents: agents })
    } catch (error) {
      console.error('Failed to fetch available agents:', error)
    }
  },

  createTask: async (agent, plan) => {
    set({ loading: true, error: null })
    try {
      const newTask = await agentService.createTask({ agent, planDescription: plan })
      set((state) => ({
        tasks: [...state.tasks, newTask],
        loading: false,
        planDescription: '',
        selectedAgent: null
      }))
    } catch (error) {
      set({ error: (error as Error).message, loading: false })
    }
  },

  executeTask: async (taskId) => {
    try {
      await agentService.executeTask({ taskId })
      set((state) => ({
        tasks: state.tasks.map((task) =>
          task.id === taskId ? { ...task, status: 'processing' as TaskStatus, startedAt: Date.now() } : task
        )
      }))
    } catch (error) {
      console.error('Failed to execute task:', error)
    }
  },

  stopTask: async (taskId) => {
    try {
      // TODO: 调用后端 API
      // await apiClient.stopTask(taskId)
      set((state) => ({
        tasks: state.tasks.map((task) => (task.id === taskId ? { ...task, status: 'failed' as TaskStatus } : task))
      }))
    } catch (error) {
      console.error('Failed to stop task:', error)
    }
  },

  deleteTask: async (taskId) => {
    try {
      await agentService.deleteTask({ taskId })
      set((state) => ({
        tasks: state.tasks.filter((task) => task.id !== taskId)
      }))
    } catch (error) {
      console.error('Failed to delete task:', error)
    }
  },

  updateTaskStatus: (taskId, updates) => {
    set((state) => ({
      tasks: state.tasks.map((task) => (task.id === taskId ? { ...task, ...updates } : task))
    }))
  },

  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
  setPlanDescription: (description) => set({ planDescription: description }),

  getTodoTasks: () => get().tasks.filter((t) => t.status === 'todo'),
  getProcessingTasks: () => get().tasks.filter((t) => t.status === 'processing'),
  getDoneTasks: () => get().tasks.filter((t) => t.status === 'done' || t.status === 'failed')
}))
