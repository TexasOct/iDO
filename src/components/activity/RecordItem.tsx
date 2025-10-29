import { RawRecord } from '@/lib/types/activity'
import { format } from 'date-fns'
import { Database, Image } from 'lucide-react'
import { ScreenshotThumbnail } from './ScreenshotThumbnail'

interface RecordItemProps {
  record: RawRecord
}

interface ScreenshotMetadata {
  action?: string
  screenshotPath?: string
  width?: number
  height?: number
  format?: string
  hash?: string
  monitor?: {
    left: number
    top: number
    width: number
    height: number
  }
}

export function RecordItem({ record }: RecordItemProps) {
  const time = format(new Date(record.timestamp), 'HH:mm:ss.SSS')

  // 检测是否为截屏事件
  const metadata = record.metadata as ScreenshotMetadata | undefined
  const isScreenshot = metadata?.action === 'capture' && metadata?.screenshotPath

  return (
    <div className="bg-background/50 flex items-start gap-2 rounded p-2 text-xs">
      {isScreenshot ? (
        <Image className="text-muted-foreground mt-0.5 h-3 w-3 flex-shrink-0" />
      ) : (
        <Database className="text-muted-foreground mt-0.5 h-3 w-3 flex-shrink-0" />
      )}
      <div className="min-w-0 flex-1">
        <div className="text-muted-foreground mb-1 flex items-center gap-2">
          <span className="font-mono">{time}</span>
        </div>
        <p className="text-foreground break-words">{record.content}</p>

        {/* 截屏缩略图 */}
        {isScreenshot && metadata?.screenshotPath && (
          <div className="mt-2">
            <ScreenshotThumbnail
              screenshotPath={metadata.screenshotPath}
              screenshotHash={metadata?.hash}
              width={280}
              height={160}
            />
          </div>
        )}

        {/* 非截屏事件的元数据 */}
        {!isScreenshot && record.metadata && Object.keys(record.metadata).length > 0 && (
          <pre className="text-muted-foreground bg-muted/50 mt-1 overflow-x-auto rounded p-1 text-[10px]">
            {JSON.stringify(record.metadata, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
