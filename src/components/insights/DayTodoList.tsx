import { X, MessageSquare, Trash2, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'
import { useTranslation } from 'react-i18next'

interface DayTodoListProps {
  selectedDate: string
  todos: InsightTodo[]
  onClose: () => void
  onExecuteInChat: (todoId: string) => void
  onDelete: (todoId: string) => void
  onComplete?: (todoId: string) => void
}

export function DayTodoList({ selectedDate, todos, onClose, onExecuteInChat, onDelete, onComplete }: DayTodoListProps) {
  const { t } = useTranslation()

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long'
    })
  }

  return (
    <div className="bg-background flex h-full flex-col border-l">
      {/* 头部 */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <h3 className="font-semibold">{formatDate(selectedDate)}</h3>
          <p className="text-muted-foreground text-xs">
            {todos.length} {t('insights.todosCount', '个待办')}
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* 任务列表 */}
      <ScrollArea className="flex-1">
        {todos.length === 0 ? (
          <div className="flex h-32 items-center justify-center">
            <p className="text-muted-foreground text-sm">{t('insights.noTodosForDay', '当天没有待办')}</p>
          </div>
        ) : (
          <div className="space-y-3 p-4">
            {todos.map((todo) => (
              <Card key={todo.id} className={cn('border-l-4 border-l-blue-500')}>
                <div className="p-4">
                  {/* 标题 */}
                  <div className="mb-2 flex items-start justify-between">
                    <h4 className="leading-tight font-medium">{todo.title}</h4>
                    {todo.completed && (
                      <Badge variant="outline" className="text-xs">
                        {t('insights.completed', '已完成')}
                      </Badge>
                    )}
                  </div>

                  {/* 描述 */}
                  {todo.description && (
                    <p className="text-muted-foreground mb-3 text-sm leading-relaxed">{todo.description}</p>
                  )}

                  {/* 关键词 */}
                  {todo.keywords && todo.keywords.length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-1">
                      {todo.keywords.slice(0, 3).map((keyword, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {keyword}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* 操作按钮 */}
                  {!todo.completed && (
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => onExecuteInChat(todo.id)} className="flex-1">
                        <MessageSquare className="mr-1 h-3.5 w-3.5" />
                        {t('insights.executeInChat', 'Agent执行')}
                      </Button>
                      {onComplete && (
                        <Button size="sm" variant="outline" onClick={() => onComplete(todo.id)}>
                          <Check className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onDelete(todo.id)}
                        className="text-destructive hover:bg-destructive/10 hover:text-destructive">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
