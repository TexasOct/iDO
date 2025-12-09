import { useEffect, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, RefreshCw, Trash2, MessageSquare } from 'lucide-react'
import { useInsightsStore } from '@/lib/stores/insights'
import { TimeDisplay } from '@/components/shared/TimeDisplay'
import { StickyTimelineGroup } from '@/components/shared/StickyTimelineGroup'
import { fetchKnowledgeCountByDate } from '@/lib/services/insights'
import { emitKnowledgeToChat } from '@/lib/events/eventBus'
import { useNavigate } from 'react-router'
import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { ScrollToTop } from '@/components/shared/ScrollToTop'

export default function AIKnowledgeView() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const knowledge = useInsightsStore((state) => state.knowledge)
  const loading = useInsightsStore((state) => state.loadingKnowledge)
  const refreshKnowledge = useInsightsStore((state) => state.refreshKnowledge)
  const removeKnowledge = useInsightsStore((state) => state.removeKnowledge)
  const lastError = useInsightsStore((state) => state.lastError)
  const clearError = useInsightsStore((state) => state.clearError)
  const [dateCountMap, setDateCountMap] = useState<Record<string, number>>({})

  useEffect(() => {
    void refreshKnowledge()

    // Fetch daily totals asynchronously (avoid blocking the UI)
    fetchKnowledgeCountByDate()
      .then((counts) => setDateCountMap(counts))
      .catch((err) => console.error('[AIKnowledgeView] Failed to fetch date counts', err))
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

  const handleSendToChat = (item: any) => {
    toast.success(t('insights.redirectingToChat'))
    navigate('/chat')

    setTimeout(() => {
      emitKnowledgeToChat({
        knowledgeId: item.id,
        title: item.title,
        description: item.description,
        keywords: item.keywords || [],
        createdAt: item.createdAt || Date.now()
      })
      console.log('[AIKnowledgeView] Delay 200ms before emitting knowledge event')
    }, 200)
  }

  return (
    <PageLayout>
      <PageHeader
        title={t('insights.knowledgeSummary')}
        description={t('insights.knowledgePageDescription')}
        actions={
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            {t('common.refresh')}
          </Button>
        }
      />

      <div className="flex flex-1 flex-col gap-6 overflow-hidden">
        {loading && knowledge.length === 0 ? (
          <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('insights.loading')}
          </div>
        ) : knowledge.length === 0 ? (
          <div className="flex flex-1 items-center justify-center text-center">
            <div className="space-y-2">
              <h3 className="text-foreground text-lg font-semibold">{t('insights.noKnowledge')}</h3>
              <p className="text-muted-foreground text-sm">{t('activity.noDataDescription')}</p>
            </div>
          </div>
        ) : (
          <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
            <StickyTimelineGroup
              items={knowledge}
              getDate={(item) => item.createdAt}
              renderItem={(item) => (
                <Card className="shadow-sm">
                  <CardHeader>
                    <div className="flex items-start gap-3">
                      <div className="flex-1">
                        <CardTitle className="text-lg leading-tight">{item.title}</CardTitle>
                        {item.createdAt && (
                          <CardDescription className="mt-1">
                            <TimeDisplay timestamp={item.createdAt} showDate={true} />
                          </CardDescription>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleSendToChat(item)}
                          className="h-8 w-8"
                          title="Send to chat">
                          <MessageSquare className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)} className="h-8 w-8">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-muted-foreground text-sm leading-6 whitespace-pre-wrap">{item.description}</p>
                    {item.keywords.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {item.keywords.map((keyword, index) => (
                          <Badge key={`${item.id}-${keyword}-${index}`} variant="primary" className="text-xs">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
              emptyMessage={t('insights.noKnowledge')}
              countText={(count) => `${count} ${t('insights.knowledgeCount')}`}
              dateCountMap={dateCountMap}
            />
          </div>
        )}
      </div>
      <ScrollToTop containerRef={scrollContainerRef} />
    </PageLayout>
  )
}
