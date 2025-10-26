/**
 * ActivityContext 组件
 * 显示关联的活动上下文信息（精简版）
 */

import { useEffect, useState } from 'react'
import { Activity } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { Button } from '@/components/ui/button'
import { X, Link2, ChevronDown, ChevronUp } from 'lucide-react'
import { format } from 'date-fns'
import { useTranslation } from 'react-i18next'

interface ActivityContextProps {
  activityId: string
  onDismiss: () => void
}

export function ActivityContext({ activityId, onDismiss }: ActivityContextProps) {
  const { t } = useTranslation()
  const [activity, setActivity] = useState<Activity | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const timelineData = useActivityStore((state) => state.timelineData)

  useEffect(() => {
    // 从 store 的 timelineData 中查找活动
    const findActivity = () => {
      for (const day of timelineData) {
        const found = day.activities.find((a) => a.id === activityId)
        if (found) {
          setActivity(found)
          setLoading(false)
          return
        }
      }
      // 如果没找到，标记为加载失败
      setLoading(false)
    }

    findActivity()
  }, [activityId, timelineData])

  if (loading) {
    return (
      <div className="border-primary/30 bg-primary/5 flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
        <Link2 className="text-primary h-3.5 w-3.5" />
        <span className="text-muted-foreground">{t('chat.loadingContext')}</span>
      </div>
    )
  }

  if (!activity) {
    return null
  }

  const time = format(new Date(activity.timestamp), 'HH:mm:ss')

  return (
    <div className="border-primary/30 bg-primary/5 rounded-md border">
      {/* 精简的头部 */}
      <div className="flex items-center gap-2 px-3 py-2">
        <Link2 className="text-primary h-3.5 w-3.5 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-primary text-xs font-medium">{t('chat.relatedActivity')}</span>
            <span className="text-foreground truncate text-sm font-medium">{activity.title}</span>
            <span className="text-muted-foreground text-xs">({time})</span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded(!expanded)}
          className="text-muted-foreground hover:text-foreground h-6 px-1.5 text-xs"
          title={expanded ? t('chat.hideDetails') : t('chat.viewDetails')}>
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          className="text-muted-foreground hover:text-foreground h-6 w-6 p-0"
          title={t('common.cancel')}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* 展开的详情 */}
      {expanded && (
        <div className="border-primary/20 border-t px-3 py-2">
          {activity.description && (
            <div className="text-muted-foreground mb-2 text-xs">
              <span className="font-medium">{t('activity.details')}: </span>
              {activity.description}
            </div>
          )}
          {activity.eventSummaries && activity.eventSummaries.length > 0 && (
            <div className="text-xs">
              <div className="text-muted-foreground mb-1 font-medium">
                {t('activity.eventSummariesCount').replace(' ', '')}: {activity.eventSummaries.length}
              </div>
              <div className="space-y-0.5">
                {activity.eventSummaries.slice(0, 3).map((summary) => (
                  <div key={summary.id} className="text-muted-foreground truncate">
                    • {summary.title}
                  </div>
                ))}
                {activity.eventSummaries.length > 3 && (
                  <div className="text-muted-foreground">
                    ... {t('common.and')} {activity.eventSummaries.length - 3} {t('common.more')}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
