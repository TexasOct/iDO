import { RawRecord } from '@/lib/types/activity'
import { format } from 'date-fns'
import { Database } from 'lucide-react'

interface RecordItemProps {
  record: RawRecord
}

export function RecordItem({ record }: RecordItemProps) {
  const time = format(new Date(record.timestamp), 'HH:mm:ss.SSS')

  return (
    <div className="flex items-start gap-2 text-xs bg-background/50 rounded p-2">
      <Database className="h-3 w-3 text-muted-foreground mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 text-muted-foreground mb-1">
          <span className="font-mono">{time}</span>
        </div>
        <p className="text-foreground break-words">{record.content}</p>
        {record.metadata && Object.keys(record.metadata).length > 0 && (
          <pre className="mt-1 text-[10px] text-muted-foreground bg-muted/50 rounded p-1 overflow-x-auto">{JSON.stringify(record.metadata, null, 2)}</pre>
        )}
      </div>
    </div>
  )
}
