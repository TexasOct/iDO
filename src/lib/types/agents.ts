// Agents 相关类型定义

export type AgentType = 'WritingAgent' | 'ResearchAgent' | 'AnalysisAgent' | string

export type TaskStatus = 'todo' | 'processing' | 'done' | 'failed'

export interface AgentTask {
  id: string
  agent: AgentType
  planDescription: string
  status: TaskStatus
  createdAt: number
  startedAt?: number
  completedAt?: number
  duration?: number // 运行时长（秒）
  result?: {
    type: 'text' | 'file'
    content: string
    filePath?: string
  }
  error?: string
}

export interface AgentConfig {
  name: AgentType
  description: string
  icon?: string
}
