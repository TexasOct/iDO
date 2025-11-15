import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useInsightsStore } from '@/lib/stores/insights'
import { PendingTodoList } from '@/components/insights/PendingTodoList'
import { TodoCalendarView } from '@/components/insights/TodoCalendarView'
import { DayTodoList } from '@/components/insights/DayTodoList'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { Bot } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { emitTodoToChat } from '@/lib/events/eventBus'
import {
  registerTodoDropHandler,
  unregisterTodoDropHandler,
  type DraggedTodoData,
  type TodoDragTarget
} from '@/lib/drag/todoDragController'

export default function AITodosView() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

  // Insights store
  const todos = useInsightsStore((state) => state.todos)
  const loading = useInsightsStore((state) => state.loadingTodos)
  const refreshTodos = useInsightsStore((state) => state.refreshTodos)
  const removeTodo = useInsightsStore((state) => state.removeTodo)
  const scheduleTodo = useInsightsStore((state) => state.scheduleTodo)
  const getPendingTodos = useInsightsStore((state) => state.getPendingTodos)
  const getScheduledTodos = useInsightsStore((state) => state.getScheduledTodos)
  const getTodosByDate = useInsightsStore((state) => state.getTodosByDate)

  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  useEffect(() => {
    void refreshTodos(false) // 只加载未完成的
  }, [refreshTodos])

  const pendingTodos = getPendingTodos()
  const scheduledTodos = getScheduledTodos()
  const dayTodos = selectedDate ? getTodosByDate(selectedDate) : []

  // 处理在 Chat 中执行任务（Agent执行）
  const handleExecuteInChat = async (todoId: string) => {
    const todo = todos.find((t) => t.id === todoId)
    if (!todo) return

    try {
      toast.success('正在跳转到对话...')
      navigate('/chat')

      // 延迟 200ms 发布事件
      setTimeout(() => {
        emitTodoToChat({
          todoId: todo.id,
          title: todo.title,
          description: todo.description,
          keywords: todo.keywords,
          createdAt: todo.createdAt
        })
      }, 200)
    } catch (error) {
      console.error('Failed to execute todo in chat:', error)
      toast.error('在对话中执行任务失败')
    }
  }

  // 处理删除任务
  const handleDeleteTodo = async (todoId: string) => {
    try {
      await removeTodo(todoId)
      toast.success(t('insights.todoDeleted', '待办已删除'))
    } catch (error) {
      console.error('Failed to delete todo:', error)
      toast.error(t('insights.deleteFailed', '删除待办失败'))
    }
  }

  // 处理将任务拖拽到日历
  const formatScheduledLabel = useCallback(
    (date: string, time?: string) => {
      try {
        const locale = i18n.language?.startsWith('zh') ? 'zh-CN' : 'en-US'
        const iso = time ? `${date}T${time}` : `${date}T00:00`
        const formatter = new Intl.DateTimeFormat(locale, {
          month: 'short',
          day: 'numeric',
          ...(time
            ? {
                hour: '2-digit',
                minute: '2-digit'
              }
            : {})
        })
        return formatter.format(new Date(iso))
      } catch {
        return time ? `${date} ${time}` : date
      }
    },
    [i18n.language]
  )

  const handleDropToCalendar = useCallback(
    async (todoId: string, date: string, time?: string) => {
      try {
        setSelectedDate(date)
        await scheduleTodo(todoId, date, time)
        const label = formatScheduledLabel(date, time)
        toast.success(`${t('insights.todoScheduled', '待办已调度')} · ${label}`)
      } catch (error) {
        console.error('Failed to schedule todo:', error)
        toast.error(t('insights.scheduleFailed', '调度待办失败'))
      }
    },
    [formatScheduledLabel, scheduleTodo, t]
  )

  const dropHandler = useCallback(
    (todo: DraggedTodoData, target: TodoDragTarget) => {
      void handleDropToCalendar(todo.id, target.date, target.time)
    },
    [handleDropToCalendar]
  )

  useEffect(() => {
    registerTodoDropHandler(dropHandler)
    return () => {
      unregisterTodoDropHandler(dropHandler)
    }
  }, [dropHandler])

  if (loading && todos.length === 0) {
    return <LoadingPage message={t('insights.loading', '加载中...')} />
  }

  return (
    <div className="flex h-full">
      {/* 左侧：日历 */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="shrink-0 px-6 py-4">
          <div>
            <h1 className="text-2xl font-semibold">{t('insights.calendar', '日历')}</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              {t('insights.calendarDesc', '拖拽待办到日历来调度执行时间')}
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          <TodoCalendarView todos={scheduledTodos} selectedDate={selectedDate} onDateSelect={setSelectedDate} />
        </div>
      </div>

      {/* 中间：Pending 区域 */}
      <div className="flex w-80 flex-col border-r border-l">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold">{t('insights.pendingTodos', '待办列表')}</h2>
              <p className="text-muted-foreground text-xs">
                {pendingTodos.length} {t('insights.todosCount', '个待办')}
              </p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-x-hidden overflow-y-auto">
          {pendingTodos.length === 0 ? (
            <EmptyState
              icon={Bot}
              title={t('insights.noPendingTodos', '暂无待处理待办')}
              description={t('insights.todosGeneratedFromActivities', 'AI 会从你的活动中自动生成待办')}
            />
          ) : (
            <PendingTodoList todos={pendingTodos} onExecuteInChat={handleExecuteInChat} onDelete={handleDeleteTodo} />
          )}
        </div>
      </div>

      {/* 右侧：选中日期的待办列表 */}
      {selectedDate && (
        <div className="w-80">
          <DayTodoList
            selectedDate={selectedDate}
            todos={dayTodos}
            onClose={() => setSelectedDate(null)}
            onExecuteInChat={handleExecuteInChat}
            onDelete={handleDeleteTodo}
          />
        </div>
      )}
    </div>
  )
}
