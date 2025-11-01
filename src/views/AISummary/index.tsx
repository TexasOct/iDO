import React, { useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { useInsightsStore } from '@/lib/stores/insights'

export default function AISummaryView() {
  const { t } = useTranslation()

  const knowledge = useInsightsStore((state) => state.knowledge)
  const todos = useInsightsStore((state) => state.todos)
  const diaries = useInsightsStore((state) => state.diaries)
  const loadingKnowledge = useInsightsStore((state) => state.loadingKnowledge)
  const loadingTodos = useInsightsStore((state) => state.loadingTodos)
  const loadingDiaries = useInsightsStore((state) => state.loadingDiaries)
  const refreshKnowledge = useInsightsStore((state) => state.refreshKnowledge)
  const refreshTodos = useInsightsStore((state) => state.refreshTodos)
  const refreshDiaries = useInsightsStore((state) => state.refreshDiaries)
  const removeKnowledge = useInsightsStore((state) => state.removeKnowledge)
  const removeTodo = useInsightsStore((state) => state.removeTodo)
  const removeDiary = useInsightsStore((state) => state.removeDiary)
  const createDiaryForDate = useInsightsStore((state) => state.createDiaryForDate)
  const lastError = useInsightsStore((state) => state.lastError)
  const clearError = useInsightsStore((state) => state.clearError)

  useEffect(() => {
    refreshKnowledge()
    refreshTodos()
    refreshDiaries()
  }, [refreshKnowledge, refreshTodos, refreshDiaries])

  useEffect(() => {
    if (!lastError) return
    toast.error(lastError)
    clearError()
  }, [lastError, clearError])

  const handleRefreshAll = async () => {
    try {
      await Promise.all([refreshKnowledge(), refreshTodos(), refreshDiaries()])
      toast.success(t('insights.refreshSummarySuccess'))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error))
    }
  }

  const handleGenerateTodayDiary = async () => {
    try {
      const today = new Date().toISOString().slice(0, 10)
      await createDiaryForDate(today)
      toast.success(t('insights.generateDiarySuccess'))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t('insights.summaryPageTitle')}</h1>
        <p className="text-muted-foreground text-sm">{t('insights.summaryPageDescription')}</p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" onClick={handleRefreshAll} disabled={loadingKnowledge || loadingTodos || loadingDiaries}>
          {loadingKnowledge || loadingTodos || loadingDiaries ? t('insights.loading') : t('insights.refreshSummary')}
        </Button>
        <Button size="sm" variant="secondary" onClick={handleGenerateTodayDiary} disabled={loadingDiaries}>
          {t('insights.generateToday')}
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        <SummarySection
          title={t('insights.knowledgeSummary')}
          loading={loadingKnowledge}
          emptyText={t('insights.noKnowledge')}>
          {knowledge.map((item) => (
            <SummaryCard
              key={item.id}
              title={item.title}
              description={item.description}
              keywords={item.keywords}
              deleteLabel={t('common.delete')}
              onDelete={async () => {
                try {
                  await removeKnowledge(item.id)
                  toast.success(t('insights.deleteSuccess'))
                } catch (error) {
                  toast.error(error instanceof Error ? error.message : String(error))
                }
              }}
            />
          ))}
        </SummarySection>

        <SummarySection title={t('insights.todoSummary')} loading={loadingTodos} emptyText={t('insights.noTodos')}>
          {todos.map((todo) => (
            <SummaryCard
              key={todo.id}
              title={todo.title}
              description={todo.description}
              keywords={todo.keywords}
              status={todo.completed ? t('insights.todoCompleted') : t('insights.todoPending')}
              deleteLabel={t('common.delete')}
              onDelete={async () => {
                try {
                  await removeTodo(todo.id)
                  toast.success(t('insights.deleteSuccess'))
                } catch (error) {
                  toast.error(error instanceof Error ? error.message : String(error))
                }
              }}
            />
          ))}
        </SummarySection>

        <SummarySection title={t('insights.diarySummary')} loading={loadingDiaries} emptyText={t('insights.noDiaries')}>
          {diaries.map((diary) => (
            <Card key={diary.id} className="h-full">
              <CardHeader>
                <CardTitle className="text-base">{diary.date}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-muted-foreground text-sm leading-6 whitespace-pre-line">{diary.content}</p>
              </CardContent>
              <CardFooter className="justify-end space-x-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={async () => {
                    try {
                      await removeDiary(diary.id)
                      toast.success(t('insights.deleteSuccess'))
                    } catch (error) {
                      toast.error(error instanceof Error ? error.message : String(error))
                    }
                  }}>
                  {t('common.delete')}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </SummarySection>
      </div>
    </div>
  )
}

interface SummarySectionProps {
  title: string
  loading: boolean
  emptyText: string
  children: React.ReactNode
}

function SummarySection({ title, loading, emptyText, children }: SummarySectionProps) {
  const hasChildren = useMemo(() => {
    return React.Children.count(children) > 0
  }, [children])

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <Separator className="mt-2" />
      </div>
      {loading && !hasChildren ? (
        <p className="text-muted-foreground text-sm">{emptyText}</p>
      ) : hasChildren ? (
        <div className="flex flex-col gap-4">{children}</div>
      ) : (
        <p className="text-muted-foreground text-sm">{emptyText}</p>
      )}
    </div>
  )
}

interface SummaryCardProps {
  title?: string
  description?: string
  keywords?: string[]
  status?: string
  deleteLabel?: string
  onDelete?: () => Promise<void>
}

function SummaryCard({ title, description, keywords, status, deleteLabel, onDelete }: SummaryCardProps) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {status && <CardDescription>{status}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-3">
        {description && <p className="text-muted-foreground text-sm leading-6 whitespace-pre-line">{description}</p>}
        {keywords && keywords.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {keywords.map((keyword) => (
              <Badge key={keyword} variant="secondary">
                {keyword}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
      {onDelete && (
        <CardFooter className="justify-end">
          <Button size="sm" variant="ghost" onClick={onDelete}>
            {deleteLabel}
          </Button>
        </CardFooter>
      )}
    </Card>
  )
}
