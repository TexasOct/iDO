import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import { useInsightsStore } from '@/lib/stores/insights'

export default function AITodosView() {
  const { t } = useTranslation()
  const todos = useInsightsStore((state) => state.todos)
  const loading = useInsightsStore((state) => state.loadingTodos)
  const refreshTodos = useInsightsStore((state) => state.refreshTodos)
  const removeTodo = useInsightsStore((state) => state.removeTodo)
  const includeCompleted = useInsightsStore((state) => state.todoIncludeCompleted)
  const lastError = useInsightsStore((state) => state.lastError)
  const clearError = useInsightsStore((state) => state.clearError)

  useEffect(() => {
    void refreshTodos()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!lastError) return
    toast.error(lastError)
    clearError()
  }, [lastError, clearError])

  const handleRefresh = () => {
    void refreshTodos(includeCompleted)
  }

  const handleToggleCompleted = (checked: boolean) => {
    void refreshTodos(checked)
  }

  const handleDelete = async (id: string) => {
    try {
      await removeTodo(id)
      toast.success(t('insights.deleteSuccess'))
    } catch (error) {
      toast.error((error as Error).message)
    }
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t('insights.todoSummary')}</h1>
        <p className="text-muted-foreground text-sm">{t('insights.todoPageDescription')}</p>
      </header>

      <div className="flex flex-wrap items-center gap-4">
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          {t('common.refresh')}
        </Button>
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <Switch checked={includeCompleted} onCheckedChange={handleToggleCompleted} id="include-completed" />
          <label htmlFor="include-completed">{t('insights.includeCompleted')}</label>
        </div>
      </div>

      {loading && todos.length === 0 ? (
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('insights.loading')}
        </div>
      ) : todos.length === 0 ? (
        <div className="border-muted/60 rounded-2xl border border-dashed p-10 text-center">
          <p className="text-muted-foreground text-sm">{t('insights.noTodos')}</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {todos.map((todo) => (
            <Card key={todo.id} className="shadow-sm">
              <CardHeader>
                <div className="flex items-start gap-3">
                  <div className="flex-1">
                    <CardTitle className="text-lg leading-tight">{todo.title}</CardTitle>
                    <CardDescription className="text-muted-foreground mt-1 text-xs">
                      {todo.createdAt ? new Date(todo.createdAt).toLocaleString() : null}
                    </CardDescription>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(todo.id)} className="h-8 w-8">
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
                    {todo.keywords.map((keyword) => (
                      <Badge key={keyword} variant="secondary" className="text-xs">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
