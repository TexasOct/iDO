import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Trash2 } from 'lucide-react'
import DiaryContent from '@/components/shared/DiaryContent'

export interface DiaryItem {
  id: string
  date: string
  content: string
  createdAt?: string
}

interface DiaryCardProps {
  diary: DiaryItem
  onDelete: (id: string) => void
}

export function DiaryCard({ diary, onDelete }: DiaryCardProps) {
  return (
    <Card className="shadow-sm">
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <CardTitle className="text-lg leading-tight">{diary.date}</CardTitle>
            <CardDescription className="text-muted-foreground mt-1 text-xs">
              {diary.createdAt ? new Date(diary.createdAt).toLocaleString() : null}
            </CardDescription>
          </div>
          <Button variant="ghost" size="icon" onClick={() => onDelete(diary.id)} className="h-8 w-8">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <DiaryContent text={diary.content} />
      </CardContent>
    </Card>
  )
}
