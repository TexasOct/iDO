import { create } from 'zustand'
import { AgentTask, AgentType, AgentConfig, TaskStatus } from '@/lib/types/agents'

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
      // TODO: 调用后端 API
      // const tasks = await apiClient.getTasks()

      // 模拟数据用于测试
      const mockTasks: AgentTask[] = [
        {
          id: 'task-1',
          agent: 'WritingAgent',
          planDescription: '帮我写一篇关于 React 19 新特性的技术博客',
          status: 'todo',
          createdAt: Date.now() - 3600000
        },
        {
          id: 'task-2',
          agent: 'ResearchAgent',
          planDescription: '收集关于 Tauri 桌面应用开发的最佳实践',
          status: 'processing',
          createdAt: Date.now() - 7200000,
          startedAt: Date.now() - 3600000,
          duration: 1800
        },
        {
          id: 'task-3',
          agent: 'AnalysisAgent',
          planDescription: '分析最近一周的代码提交情况',
          status: 'done',
          createdAt: Date.now() - 86400000,
          startedAt: Date.now() - 86400000 + 1000,
          completedAt: Date.now() - 82800000,
          duration: 3600,
          result: {
            type: 'text',
            content: '分析完成：共提交代码 15 次，新增功能 3 个，修复 bug 5 个'
          }
        }
      ]

      // 模拟网络延迟
      await new Promise((resolve) => setTimeout(resolve, 300))

      set({ tasks: mockTasks, loading: false })
    } catch (error) {
      set({ error: (error as Error).message, loading: false })
    }
  },

  fetchAvailableAgents: async () => {
    try {
      // TODO: 从后端获取可用 Agents
      // const agents = await apiClient.getAvailableAgents()
      // set({ availableAgents: agents })
    } catch (error) {
      console.error('Failed to fetch available agents:', error)
    }
  },

  createTask: async (agent, plan) => {
    set({ loading: true, error: null })
    try {
      // TODO: 调用后端 API
      // const newTask = await apiClient.createTask({ agent, plan })
      const newTask: AgentTask = {
        id: Date.now().toString(),
        agent,
        planDescription: plan,
        status: 'todo',
        createdAt: Date.now()
      }
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
      // TODO: 调用后端 API
      // await apiClient.executeTask(taskId)
      set((state) => ({
        tasks: state.tasks.map((task) => (task.id === taskId ? { ...task, status: 'processing' as TaskStatus, startedAt: Date.now() } : task))
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
      // TODO: 调用后端 API
      // await apiClient.deleteTask(taskId)
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
