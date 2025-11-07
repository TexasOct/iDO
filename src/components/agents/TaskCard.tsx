import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTranslation } from 'react-i18next'
import type { AgentTask } from '@/lib/types/agents'

interface TaskCardProps {
  task: AgentTask
  onExecute?: () => void
  onDelete?: () => void
}

export function TaskCard({ task, onExecute, onDelete }: TaskCardProps) {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">{task.agent}</CardTitle>
            <CardDescription className="mt-1">{task.planDescription}</CardDescription>
          </div>
          <Badge variant={task.status === 'done' ? 'default' : task.status === 'failed' ? 'destructive' : 'secondary'}>
            {task.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2">
          {task.status === 'todo' && onExecute && (
            <Button size="sm" onClick={onExecute}>
              {t('agents.execute')}
            </Button>
          )}
          {onDelete && (
            <Button size="sm" variant="outline" onClick={onDelete}>
              {t('common.delete')}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
