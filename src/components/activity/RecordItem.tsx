import { RawRecord } from '@/lib/types/activity'
import { format } from 'date-fns'
import { Database } from 'lucide-react'

interface RecordItemProps {
  record: RawRecord
}

export function RecordItem({ record }: RecordItemProps) {
  const time = format(new Date(record.timestamp), 'HH:mm:ss.SSS')

  return (
    <div className="bg-background/50 flex items-start gap-2 rounded p-2 text-xs">
      <Database className="text-muted-foreground mt-0.5 h-3 w-3 flex-shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="text-muted-foreground mb-1 flex items-center gap-2">
          <span className="font-mono">{time}</span>
        </div>
        <p className="text-foreground break-words">{record.content}</p>

        {/* 元数据 */}
        {record.metadata && Object.keys(record.metadata).length > 0 && (
          <pre className="text-muted-foreground bg-muted/50 mt-1 overflow-x-auto rounded p-1 text-[10px]">
            {JSON.stringify(record.metadata, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
