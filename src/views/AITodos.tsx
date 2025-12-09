import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useInsightsStore } from '@/lib/stores/insights'
import { PendingTodoList } from '@/components/insights/PendingTodoList'
import { TodoCalendarView } from '@/components/insights/TodoCalendarView'
import { TodosDetailDialog } from '@/components/insights/TodosDetailDialog'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { Bot } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { ScrollToTop } from '@/components/shared/ScrollToTop'
import { emitTodoToChat } from '@/lib/events/eventBus'
import { PageHeader } from '@/components/layout/PageHeader'
import type { InsightTodo, RecurrenceRule } from '@/lib/services/insights'
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
  const completeTodo = useInsightsStore((state) => state.completeTodo)
  const unscheduleTodo = useInsightsStore((state) => state.unscheduleTodo)
  const scheduleTodo = useInsightsStore((state) => state.scheduleTodo)
  const getPendingTodos = useInsightsStore((state) => state.getPendingTodos)
  const getScheduledTodos = useInsightsStore((state) => state.getScheduledTodos)
  const getTodosByDate = useInsightsStore((state) => state.getTodosByDate)

  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Get fresh todos for dialog from store (not a snapshot)
  const dialogTodos = selectedDate ? getTodosByDate(selectedDate) : []

  useEffect(() => {
    void refreshTodos(false) // Only load incomplete todos
  }, [refreshTodos])

  const pendingTodos = getPendingTodos()
  const scheduledTodos = getScheduledTodos()

  // Handle date cell click - opens dialog with todos for that date
  const handleDateClick = useCallback(
    (date: string) => {
      const todosForDate = getTodosByDate(date)
      if (todosForDate.length > 0) {
        setSelectedDate(date)
        setDialogOpen(true)
      }
    },
    [getTodosByDate]
  )

  // Handle completing a todo
  const handleCompleteTodo = useCallback(
    async (todo: InsightTodo) => {
      try {
        await completeTodo(todo.id)
        toast.success(t('insights.todoCompleted', 'Todo completed'))
        // Check if dialog should close (no more todos for this date)
        if (selectedDate) {
          const remainingTodos = getTodosByDate(selectedDate).filter((t) => t.id !== todo.id)
          if (remainingTodos.length === 0) {
            setDialogOpen(false)
          }
        }
      } catch (error) {
        console.error('Failed to complete todo:', error)
        toast.error(t('insights.completeFailed', 'Failed to complete todo'))
      }
    },
    [completeTodo, getTodosByDate, selectedDate, t]
  )

  // Handle unscheduling a todo
  const handleUnscheduleTodo = useCallback(
    async (todo: InsightTodo) => {
      try {
        await unscheduleTodo(todo.id)
        toast.success(t('insights.todoUnscheduled', 'Todo unscheduled'))
        setDialogOpen(false)
      } catch (error) {
        console.error('Failed to unschedule todo:', error)
        toast.error(t('insights.unscheduleFailed', 'Failed to unschedule todo'))
      }
    },
    [unscheduleTodo, t]
  )

  // Handle updating todo schedule (time range and recurrence)
  const handleUpdateSchedule = useCallback(
    async (
      todo: InsightTodo,
      scheduledDate: string,
      scheduledTime?: string,
      scheduledEndTime?: string,
      recurrenceRule?: RecurrenceRule
    ) => {
      console.log('[AITodos] handleUpdateSchedule called:', {
        todoId: todo.id,
        title: todo.title,
        scheduledDate,
        scheduledTime,
        scheduledEndTime,
        endTimeType: typeof scheduledEndTime,
        recurrenceRule
      })
      try {
        await scheduleTodo(todo.id, scheduledDate, scheduledTime, scheduledEndTime, recurrenceRule)
        toast.success(t('insights.scheduleUpdated', 'Schedule updated'))
        // dialogTodos will automatically update from store
      } catch (error) {
        console.error('Failed to update schedule:', error)
        toast.error(t('insights.scheduleUpdateFailed', 'Failed to update schedule'))
      }
    },
    [scheduleTodo, t]
  )

  // Handle executing a todo in Chat (agent execution)
  const handleExecuteInChat = async (todoOrId: InsightTodo | string) => {
    const todoId = typeof todoOrId === 'string' ? todoOrId : todoOrId.id
    const todo = todos.find((t) => t.id === todoId)
    if (!todo) return

    try {
      toast.success(t('insights.redirectingToChat'))
      navigate('/chat')

      // Publish the event after a 200ms delay
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
      toast.error(t('insights.executeInChatFailed'))
    }
  }

  // Handle deleting a todo
  const handleDeleteTodo = async (todoId: string) => {
    try {
      await removeTodo(todoId)
      toast.success(t('insights.todoDeleted', 'Todo deleted'))
    } catch (error) {
      console.error('Failed to delete todo:', error)
      toast.error(t('insights.deleteFailed', 'Failed to delete todo'))
    }
  }

  // Handle dragging todos onto the calendar
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

  // Helper function to calculate end time (1 hour after start time)
  const calculateEndTime = useCallback((startTime: string): string => {
    const [hours, minutes] = startTime.split(':').map(Number)
    const endHour = (hours + 1) % 24
    return `${String(endHour).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
  }, [])

  const handleDropToCalendar = useCallback(
    async (todoId: string, date: string, time?: string) => {
      console.log('[AITodos] handleDropToCalendar called:', { todoId, date, time })
      try {
        setSelectedDate(date)

        // If time is provided, automatically set end time to 1 hour later
        const startTime = time || '09:00'
        const endTime = time ? calculateEndTime(time) : '10:00'

        console.log('[AITodos] Scheduling with default duration:', { startTime, endTime })
        await scheduleTodo(todoId, date, startTime, endTime)

        const label = formatScheduledLabel(date, time)
        toast.success(`${t('insights.todoScheduled', 'Todo scheduled')} · ${label}`)
      } catch (error) {
        console.error('Failed to schedule todo:', error)
        toast.error(t('insights.scheduleFailed', 'Failed to schedule todo'))
      }
    },
    [formatScheduledLabel, scheduleTodo, t, setSelectedDate, calculateEndTime]
  )

  // Use ref to store latest handler to avoid re-registration
  const dropHandlerRef = useRef<((todo: DraggedTodoData, target: TodoDragTarget) => void) | undefined>(undefined)

  // Update ref when dependencies change
  useEffect(() => {
    dropHandlerRef.current = (todo: DraggedTodoData, target: TodoDragTarget) => {
      console.log('[AITodos] dropHandlerRef.current called:', todo, target)
      void handleDropToCalendar(todo.id, target.date, target.time)
    }
  }, [handleDropToCalendar])

  // Register stable wrapper only once
  useEffect(() => {
    const stableHandler = (todo: DraggedTodoData, target: TodoDragTarget) => {
      console.log('[AITodos] stableHandler called:', todo, target)
      dropHandlerRef.current?.(todo, target)
    }
    console.log('[AITodos] Registering drop handler')
    registerTodoDropHandler(stableHandler)
    return () => {
      console.log('[AITodos] Unregistering drop handler')
      unregisterTodoDropHandler(stableHandler)
    }
  }, [])

  if (loading && todos.length === 0) {
    return <LoadingPage message={t('insights.loading', 'Loading...')} />
  }

  return (
    <div className="flex h-full">
      {/* Left column: calendar */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <PageHeader
          title={t('insights.calendar', 'Calendar')}
          description={t('insights.calendarDesc', 'Drag todos to the calendar to schedule execution time')}
        />
        <div className="flex-1 overflow-hidden">
          <TodoCalendarView todos={scheduledTodos} selectedDate={selectedDate} onDateSelect={handleDateClick} />
        </div>
      </div>

      {/* Middle column: pending section */}
      <div className="flex w-80 flex-col border-l">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold">{t('insights.pendingTodos', 'Pending todos')}</h2>
              <p className="text-muted-foreground text-xs">
                {pendingTodos.length} {t('insights.todosCount', 'todos')}
              </p>
            </div>
          </div>
        </div>

        <div ref={scrollContainerRef} className="flex-1 overflow-x-hidden overflow-y-auto">
          {pendingTodos.length === 0 ? (
            <EmptyState
              icon={Bot}
              title={t('insights.noPendingTodos', 'No pending todos')}
              description={t(
                'insights.todosGeneratedFromActivities',
                'AI will automatically generate todos from your activities'
              )}
            />
          ) : (
            <PendingTodoList
              todos={pendingTodos}
              onExecuteInChat={handleExecuteInChat}
              onDelete={handleDeleteTodo}
              onComplete={handleCompleteTodo}
              onSchedule={handleUpdateSchedule}
            />
          )}
        </div>
        <ScrollToTop containerRef={scrollContainerRef} />
      </div>

      {/* Todos Detail Dialog */}
      <TodosDetailDialog
        todos={dialogTodos}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onComplete={handleCompleteTodo}
        onDelete={(todo) => handleDeleteTodo(todo.id)}
        onUnschedule={handleUnscheduleTodo}
        onUpdateSchedule={handleUpdateSchedule}
        onSendToChat={handleExecuteInChat}
      />
    </div>
  )
}
