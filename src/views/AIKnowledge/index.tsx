import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { useInsightsStore } from '@/lib/stores/insights'

export default function AIKnowledgeView() {
  const { t } = useTranslation()
  const knowledge = useInsightsStore((state) => state.knowledge)
  const loading = useInsightsStore((state) => state.loadingKnowledge)
  const refreshKnowledge = useInsightsStore((state) => state.refreshKnowledge)
  const removeKnowledge = useInsightsStore((state) => state.removeKnowledge)
  const lastError = useInsightsStore((state) => state.lastError)
  const clearError = useInsightsStore((state) => state.clearError)

  useEffect(() => {
    void refreshKnowledge()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!lastError) return
    toast.error(lastError)
    clearError()
  }, [lastError, clearError])

  const handleRefresh = () => {
    void refreshKnowledge()
  }

  const handleDelete = async (id: string) => {
    try {
      await removeKnowledge(id)
      toast.success(t('insights.deleteSuccess'))
    } catch (error) {
      toast.error((error as Error).message)
    }
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t('insights.knowledgeSummary')}</h1>
        <p className="text-muted-foreground text-sm">{t('insights.knowledgePageDescription')}</p>
      </header>

      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          {t('common.refresh')}
        </Button>
      </div>

      {loading && knowledge.length === 0 ? (
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('insights.loading')}
        </div>
      ) : knowledge.length === 0 ? (
        <div className="border-muted/60 rounded-2xl border border-dashed p-10 text-center">
          <p className="text-muted-foreground text-sm">{t('insights.noKnowledge')}</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {knowledge.map((item) => (
            <Card key={item.id} className="shadow-sm">
              <CardHeader>
                <div className="flex items-start gap-3">
                  <div className="flex-1">
                    <CardTitle className="text-lg leading-tight">{item.title}</CardTitle>
                    <CardDescription className="text-muted-foreground mt-1 text-xs">
                      {item.createdAt ? new Date(item.createdAt).toLocaleString() : null}
                    </CardDescription>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)} className="h-8 w-8">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-muted-foreground text-sm leading-6 whitespace-pre-wrap">{item.description}</p>
                {item.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {item.keywords.map((keyword) => (
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
