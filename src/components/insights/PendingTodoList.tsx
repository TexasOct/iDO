import { MessageSquare, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'
import { useTranslation } from 'react-i18next'

interface PendingTodoListProps {
  todos: InsightTodo[]
  onExecuteInChat: (todoId: string) => void
  onDelete: (todoId: string) => void
}

export function PendingTodoList({ todos, onExecuteInChat, onDelete }: PendingTodoListProps) {
  const { t } = useTranslation()

  const handleMouseDown = (e: React.MouseEvent, todoId: string) => {
    // 如果点击的是按钮，不触发拖拽
    if ((e.target as HTMLElement).closest('button')) {
      return
    }

    console.log('Mouse down on todo:', todoId)
    e.currentTarget.setAttribute('data-dragging', 'true')
    e.currentTarget.setAttribute('data-todo-id', todoId)
    e.currentTarget.style.opacity = '0.5'
  }

  const handleMouseUp = (e: React.MouseEvent) => {
    const draggingElement = document.querySelector('[data-dragging="true"]')
    if (draggingElement) {
      draggingElement.removeAttribute('data-dragging')
      draggingElement.removeAttribute('data-todo-id')
      ;(draggingElement as HTMLElement).style.opacity = '1'
    }
  }

  if (todos.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground text-center">
          <p className="text-sm">{t('insights.noPendingTodos', '暂无待处理待办')}</p>
          <p className="mt-1 text-xs">{t('insights.todosGeneratedFromActivities', 'AI 会从你的活动中自动生成待办')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3 p-4">
      {todos.map((todo) => (
        <div
          key={todo.id}
          onMouseDown={(e) => handleMouseDown(e, todo.id)}
          onMouseUp={handleMouseUp}
          className="cursor-move transition-opacity select-none">
          <Card className={cn('border-l-4 border-l-blue-500 transition-all hover:shadow-md')}>
            <div className="p-4">
              {/* 标题 */}
              <div className="mb-2 flex items-start justify-between gap-2">
                <h4 className="flex-1 leading-tight font-medium">{todo.title}</h4>
                <div className="flex shrink-0 gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      onExecuteInChat(todo.id)
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                    className="h-7 px-2"
                    title={t('insights.executeInChat', 'Agent执行')}>
                    <MessageSquare className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(todo.id)
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive h-7 px-2"
                    title={t('insights.discard', '舍弃')}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* 描述 */}
              {todo.description && (
                <p className="text-muted-foreground mb-2 text-sm leading-relaxed">{todo.description}</p>
              )}

              {/* 关键词 */}
              {todo.keywords && todo.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {todo.keywords.slice(0, 3).map((keyword, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </Card>
        </div>
      ))}
    </div>
  )
}
