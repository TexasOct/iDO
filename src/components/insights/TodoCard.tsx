import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export interface TodoItem {
  id: string
  title: string
  description: string
  completed?: boolean
  keywords: string[]
  createdAt?: string
}

interface TodoCardProps {
  todo: TodoItem
  onDelete: (id: string) => void
}

export function TodoCard({ todo, onDelete }: TodoCardProps) {
  const { t } = useTranslation()

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <CardTitle className="text-lg leading-tight">{todo.title}</CardTitle>
            <CardDescription className="text-muted-foreground mt-1 text-xs">
              {todo.createdAt ? new Date(todo.createdAt).toLocaleString() : null}
            </CardDescription>
          </div>
          <Button variant="ghost" size="icon" onClick={() => onDelete(todo.id)} className="h-8 w-8">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-muted-foreground text-sm leading-6 whitespace-pre-wrap">{todo.description}</p>
        <div className="flex items-center gap-2 text-xs">
          <Badge variant={todo.completed ? 'secondary' : 'outline'}>
            {todo.completed ? t('insights.todoCompleted') : t('insights.todoPending')}
          </Badge>
        </div>
        {todo.keywords.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {todo.keywords.map((keyword, index) => (
              <Badge key={`${todo.id}-${keyword}-${index}`} variant="secondary" className="text-xs">
                {keyword}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
