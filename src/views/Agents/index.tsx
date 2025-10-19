import { useEffect, useState, useCallback } from 'react'
import { useAgentsStore } from '@/lib/stores/agents'
import { EmptyState } from '@/components/shared/EmptyState'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { CreateTaskDialog } from '@/components/agents/CreateTaskDialog'
import { useTaskUpdates, TaskUpdatePayload } from '@/hooks/use-tauri-events'
import { Bot, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AgentTask } from '@/lib/types/agents'
import { useTranslation } from 'react-i18next'

function TaskCard({ task, onExecute, onDelete }: { task: AgentTask; onExecute?: () => void; onDelete?: () => void }) {
  const { t } = useTranslation()
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">{task.agent}</CardTitle>
            <CardDescription className="mt-1">{task.planDescription}</CardDescription>
          </div>
          <Badge variant={task.status === 'done' ? 'default' : task.status === 'failed' ? 'destructive' : 'secondary'}>{task.status}</Badge>
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

export default function AgentsView() {
  const { t } = useTranslation()
  const { tasks, fetchTasks, loading, getTodoTasks, getProcessingTasks, getDoneTasks, executeTask, deleteTask, updateTaskStatus } = useAgentsStore()

  const [showCreateDialog, setShowCreateDialog] = useState(false)

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // 监听后端推送的任务更新事件
  const handleTaskUpdate = useCallback(
    (payload: TaskUpdatePayload) => {
      updateTaskStatus(payload.taskId, {
        status: payload.status,
        ...(payload.progress !== undefined && { duration: payload.progress }),
        ...(payload.result && { result: payload.result }),
        ...(payload.error && { error: payload.error }),
        ...(payload.status === 'done' && { completedAt: Date.now() })
      })
    },
    [updateTaskStatus]
  )

  useTaskUpdates(handleTaskUpdate)

  const todoTasks = getTodoTasks()
  const processingTasks = getProcessingTasks()
  const doneTasks = getDoneTasks()

  if (loading && tasks.length === 0) {
    return <LoadingPage message={t('agents.loadingTasks')} />
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{t('agents.pageTitle')}</h1>
            <p className="text-sm text-muted-foreground mt-1">{t('agents.description')}</p>
          </div>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            {t('agents.createTask')}
          </Button>
        </div>
      </div>

      <CreateTaskDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />

      <div className="flex-1 overflow-y-auto p-6">
        <Tabs defaultValue="todo" className="w-full">
          <TabsList>
            <TabsTrigger value="todo">
              {t('agents.status.todo')} {todoTasks.length > 0 && <Badge className="ml-2">{todoTasks.length}</Badge>}
            </TabsTrigger>
            <TabsTrigger value="processing">
              {t('agents.status.doing')} {processingTasks.length > 0 && <Badge className="ml-2">{processingTasks.length}</Badge>}
            </TabsTrigger>
            <TabsTrigger value="done">
              {t('agents.status.done')} {doneTasks.length > 0 && <Badge className="ml-2">{doneTasks.length}</Badge>}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="todo" className="mt-6 space-y-4">
            {todoTasks.length === 0 ? (
              <EmptyState icon={Bot} title={t('agents.noTodoTasks')} description={t('agents.createTaskHint')} />
            ) : (
              todoTasks.map((task) => <TaskCard key={task.id} task={task} onExecute={() => executeTask(task.id)} onDelete={() => deleteTask(task.id)} />)
            )}
          </TabsContent>

          <TabsContent value="processing" className="mt-6 space-y-4">
            {processingTasks.length === 0 ? (
              <EmptyState icon={Bot} title={t('agents.noProcessingTasks')} />
            ) : (
              processingTasks.map((task) => <TaskCard key={task.id} task={task} />)
            )}
          </TabsContent>

          <TabsContent value="done" className="mt-6 space-y-4">
            {doneTasks.length === 0 ? (
              <EmptyState icon={Bot} title={t('agents.noDoneTasks')} />
            ) : (
              doneTasks.map((task) => <TaskCard key={task.id} task={task} onDelete={() => deleteTask(task.id)} />)
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
