import { create } from 'zustand'
import { TimelineDay } from '@/lib/types/activity'

interface ActivityState {
  timelineData: TimelineDay[]
  selectedDate: string | null
  expandedItems: Set<string> // 记录展开的节点 ID
  loading: boolean
  error: string | null

  // Actions
  fetchTimelineData: (dateRange: { start: string; end: string }) => Promise<void>
  setSelectedDate: (date: string) => void
  toggleExpanded: (id: string) => void
  expandAll: () => void
  collapseAll: () => void
}

export const useActivityStore = create<ActivityState>((set, get) => ({
  timelineData: [],
  selectedDate: null,
  expandedItems: new Set(),
  loading: false,
  error: null,

  fetchTimelineData: async (dateRange) => {
    set({ loading: true, error: null })
    try {
      // TODO: 调用后端 API
      // const data = await apiClient.getActivityTimeline(dateRange)

      // 模拟数据用于测试
      const mockData: TimelineDay[] = [
        {
          date: new Date().toISOString().split('T')[0],
          activities: [
            {
              id: 'activity-1',
              name: '编写前端代码',
              timestamp: Date.now() - 3600000,
              eventSummaries: [
                {
                  id: 'summary-1',
                  title: '实现 Activity 组件',
                  timestamp: Date.now() - 3600000,
                  events: [
                    {
                      id: 'event-1',
                      type: '键盘事件',
                      timestamp: Date.now() - 3600000,
                      summary: '在 VS Code 中编写代码',
                      records: [
                        {
                          id: 'record-1',
                          timestamp: Date.now() - 3600000,
                          content: '输入代码：import React from "react"',
                          metadata: { app: 'VS Code', file: 'Activity.tsx' }
                        },
                        {
                          id: 'record-2',
                          timestamp: Date.now() - 3500000,
                          content: '输入代码：export default function Activity() {}',
                          metadata: { app: 'VS Code', file: 'Activity.tsx' }
                        }
                      ]
                    }
                  ]
                }
              ]
            },
            {
              id: 'activity-2',
              name: '浏览技术文档',
              timestamp: Date.now() - 7200000,
              eventSummaries: [
                {
                  id: 'summary-2',
                  title: '查阅 React 文档',
                  timestamp: Date.now() - 7200000,
                  events: [
                    {
                      id: 'event-2',
                      type: '鼠标事件',
                      timestamp: Date.now() - 7200000,
                      summary: '在浏览器中浏览 React 官方文档',
                      records: [
                        {
                          id: 'record-3',
                          timestamp: Date.now() - 7200000,
                          content: '点击链接：Hooks API Reference',
                          metadata: { app: 'Chrome', url: 'https://react.dev' }
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]

      // 模拟网络延迟
      await new Promise(resolve => setTimeout(resolve, 500))

      set({ timelineData: mockData, loading: false })
    } catch (error) {
      set({ error: (error as Error).message, loading: false })
    }
  },

  setSelectedDate: (date) => set({ selectedDate: date }),

  toggleExpanded: (id) =>
    set((state) => {
      const newExpanded = new Set(state.expandedItems)
      if (newExpanded.has(id)) {
        newExpanded.delete(id)
      } else {
        newExpanded.add(id)
      }
      return { expandedItems: newExpanded }
    }),

  expandAll: () => {
    const allIds = new Set<string>()
    const { timelineData } = get()
    timelineData.forEach((day) => {
      day.activities.forEach((activity) => {
        allIds.add(activity.id)
        activity.eventSummaries.forEach((summary) => {
          allIds.add(summary.id)
          summary.events.forEach((event) => {
            allIds.add(event.id)
          })
        })
      })
    })
    set({ expandedItems: allIds })
  },

  collapseAll: () => set({ expandedItems: new Set() })
}))
