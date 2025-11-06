import { Event } from '@/lib/types/activity'
import { useActivityStore } from '@/lib/stores/activity'
import { ChevronDown, ChevronRight, Zap } from 'lucide-react'
import { format } from 'date-fns'
import { RecordItem } from './RecordItem'
import { PhotoGrid } from './PhotoGrid'
import { useTranslation } from 'react-i18next'
import { useMemo } from 'react'

interface EventItemProps {
  event: Event
}

export function EventItem({ event }: EventItemProps) {
  const { t } = useTranslation()
  // 分别订阅各个字段，避免选择器返回新对象
  const expandedItems = useActivityStore((state) => state.expandedItems)
  const toggleExpanded = useActivityStore((state) => state.toggleExpanded)
  const isExpanded = expandedItems.has(event.id)

  const startTime = format(new Date(event.startTime), 'HH:mm:ss')
  const endTime = format(new Date(event.endTime), 'HH:mm:ss')

  // 按时间倒序排序 records（最新的在上面）
  const sortedRecords = useMemo(() => {
    return [...event.records].sort((a, b) => b.timestamp - a.timestamp)
  }, [event.records])

  // 收集所有截图
  const screenshots = useMemo(() => {
    const images: string[] = []
    event.records.forEach((record) => {
      const metadata = record.metadata as { action?: string; screenshotPath?: string } | undefined
      if (metadata?.action === 'capture' && metadata?.screenshotPath) {
        images.push(metadata.screenshotPath)
      }
    })
    return images
  }, [event.records])

  // 过滤出非截图的 records
  const nonScreenshotRecords = useMemo(() => {
    return sortedRecords.filter((record) => {
      const metadata = record.metadata as { action?: string } | undefined
      return metadata?.action !== 'capture'
    })
  }, [sortedRecords])

  return (
    <div className="bg-muted/30 rounded-lg p-3">
      <button onClick={() => toggleExpanded(event.id)} className="group flex w-full items-start gap-2 text-left">
        <div className="mt-0.5">
          {isExpanded ? (
            <ChevronDown className="text-muted-foreground h-3 w-3" />
          ) : (
            <ChevronRight className="text-muted-foreground h-3 w-3" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Zap className="text-muted-foreground h-3 w-3" />
            <span className="group-hover:text-primary text-sm font-medium transition-colors">
              {startTime} - {endTime}
            </span>
          </div>
          <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
            <span>
              {event.records.length}
              {t('activity.recordsCount')}
            </span>
          </div>
        </div>
      </button>

      {isExpanded && (
        <div className="mt-3 space-y-3 pl-5">
          {/* 截图照片墙 */}
          {screenshots.length > 0 && (
            <div className="mb-3">
              <PhotoGrid images={screenshots} title={`${startTime} - ${endTime}`} />
            </div>
          )}

          {/* 非截图记录 */}
          {nonScreenshotRecords.length > 0 && (
            <div className="space-y-1">
              {nonScreenshotRecords.map((record) => (
                <RecordItem key={record.id} record={record} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
