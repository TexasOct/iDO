/**
 * PendingTodoTimeline Component
 *
 * Timeline view for pending todos grouped by creation date.
 * Features:
 * - Sticky date headers (like activity timeline)
 * - View details in dialog
 * - Drag and drop support
 * - Execute in chat and delete actions
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageSquare, Trash2, Eye, GripVertical } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'
import { TodoDetailDialog } from './TodoDetailDialog'
import { beginTodoPointerDrag } from '@/lib/drag/todoDragController'
import { StickyTimelineGroup } from '@/components/shared/StickyTimelineGroup'

interface PendingTodoListProps {
  todos: InsightTodo[]
  onExecuteInChat: (todoId: string) => void
  onDelete: (todoId: string) => void
}

export function PendingTodoList({ todos, onExecuteInChat, onDelete }: PendingTodoListProps) {
  const { t } = useTranslation()
  const [selectedTodo, setSelectedTodo] = useState<InsightTodo | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [expandedTodoId, setExpandedTodoId] = useState<string | null>(null)

  const handleViewDetails = (todo: InsightTodo) => {
    setSelectedTodo(todo)
    setDialogOpen(true)
    setExpandedTodoId(null) // Close the slide when opening dialog
  }

  const toggleCardExpand = (todoId: string) => {
    setExpandedTodoId((prev) => (prev === todoId ? null : todoId))
  }

  const handlePointerDown = (e: React.PointerEvent<HTMLElement>, todo: InsightTodo) => {
    if ((e.target as HTMLElement).closest('button')) return
    beginTodoPointerDrag(e, todo)
  }

  const renderTodoCard = (todo: InsightTodo) => {
    const isExpanded = expandedTodoId === todo.id
    return (
      <div
        data-todo-container
        data-todo-id={todo.id}
        className={cn(
          'relative overflow-hidden transition-all duration-300',
          isExpanded ? 'rounded-l-md' : 'rounded-md'
        )}>
        {/* Background Action Buttons */}
        <div className="absolute inset-y-0 right-0 flex items-stretch">
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleViewDetails(todo)
            }}
            className={cn(
              'flex w-14 flex-col items-center justify-center gap-0.5 bg-slate-600 text-white transition-all duration-300 hover:bg-slate-700',
              isExpanded ? 'translate-x-0 opacity-100 delay-[50ms]' : 'translate-x-4 opacity-0'
            )}
            title={t('insights.viewDetails', '查看详情')}>
            <Eye className="h-4 w-4" />
            <span className="text-[10px] leading-none">{t('insights.viewDetails', '详情')}</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onExecuteInChat(todo.id)
            }}
            className={cn(
              'flex w-14 flex-col items-center justify-center gap-0.5 bg-teal-700 text-white transition-all duration-300 hover:bg-teal-800',
              isExpanded ? 'translate-x-0 opacity-100 delay-100' : 'translate-x-4 opacity-0'
            )}
            title={t('insights.executeInChat', 'Agent执行')}>
            <MessageSquare className="h-4 w-4" />
            <span className="text-[10px] leading-none">{t('common.chat', '对话')}</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete(todo.id)
              setExpandedTodoId(null)
            }}
            className={cn(
              'flex w-14 flex-col items-center justify-center gap-0.5 rounded-r-lg bg-red-700 text-white transition-all duration-300 hover:bg-red-800',
              isExpanded ? 'translate-x-0 opacity-100 delay-150' : 'translate-x-4 opacity-0'
            )}
            title={t('insights.discard', '舍弃')}>
            <Trash2 className="h-4 w-4" />
            <span className="text-[10px] leading-none">{t('common.delete', '删除')}</span>
          </button>
        </div>

        {/* Slideable Card */}
        <div className={cn('relative transition-transform duration-300 ease-out', isExpanded && '-translate-x-42')}>
          <Card
            onPointerDown={(e) => handlePointerDown(e, todo)}
            className={cn(
              'gap-2 border-l-4 border-l-blue-500 py-3 transition-all hover:shadow-md',
              isExpanded ? 'rounded-r-none' : ''
            )}>
            <div className="flex min-h-9 items-center gap-1 px-2 py-1.5">
              {/* 拖拽手柄 */}
              <div
                className={cn(
                  'text-muted-foreground -ml-1 flex shrink-0 items-center rounded px-1 py-2 transition-colors',
                  isExpanded ? 'pointer-events-none opacity-0' : 'hover:bg-accent hover:text-foreground cursor-move'
                )}
                aria-hidden={isExpanded}
                title={t('insights.dragToSchedule', '拖拽到日历进行调度')}>
                <GripVertical className="h-5 w-5" />
              </div>
              {/* Todo 内容 */}
              <div className="flex-1 cursor-pointer" onClick={() => toggleCardExpand(todo.id)}>
                <h4 className="text-sm leading-tight font-medium">{todo.title}</h4>
              </div>
            </div>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <>
      <StickyTimelineGroup
        items={todos}
        getDate={(todo) => todo.createdAt}
        renderItem={renderTodoCard}
        emptyMessage={t('insights.noPendingTodos', '暂无待处理待办')}
        countText={(count) => `${count} ${t('insights.todosCount', '个待办')}`}
        headerClassName="px-5 pt-3 pb-1.5"
        headerTitleClassName="text-sm font-semibold"
        headerCountClassName="text-xs"
        itemsContainerClassName="space-y-2 px-3 pb-3"
      />

      {/* Detail Dialog */}
      <TodoDetailDialog todo={selectedTodo} open={dialogOpen} onOpenChange={setDialogOpen} />
    </>
  )
}
