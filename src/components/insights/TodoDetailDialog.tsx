/**
 * TodoDetailDialog Component
 *
 * Modal dialog to display full todo details including description and keywords
 */

import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { InsightTodo } from '@/lib/services/insights'
import { format } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'
import { CalendarClock, CalendarDays, Tag } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface TodoDetailDialogProps {
  todo: InsightTodo | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TodoDetailDialog({ todo, open, onOpenChange }: TodoDetailDialogProps) {
  const { t, i18n } = useTranslation()

  if (!todo) return null

  const locale = i18n.language === 'zh-CN' ? zhCN : enUS
  const createdDate = todo.createdAt
    ? format(new Date(todo.createdAt), i18n.language === 'zh-CN' ? 'yyyy年MM月dd日 HH:mm' : 'MMM d, yyyy HH:mm', {
        locale
      })
    : null
  const scheduledDateDisplay = todo.scheduledDate
    ? `${todo.scheduledDate}${todo.scheduledTime ? ` ${todo.scheduledTime}` : ''}`
    : t('insights.notScheduled', '未设置计划')

  const infoItems: Array<{ label: string; value: string | null; Icon: LucideIcon }> = [
    {
      label: t('insights.createdAt', '创建时间'),
      value: createdDate,
      Icon: CalendarClock
    },
    {
      label: t('insights.scheduledDate', '计划日期'),
      value: scheduledDateDisplay,
      Icon: CalendarDays
    }
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl lg:max-w-2xl">
        <DialogHeader className="mb-5 pr-12 sm:pr-16">
          <div className="flex flex-col gap-2 space-y-3 sm:flex-row sm:items-start sm:justify-between">
            <DialogTitle className="text-xl leading-tight font-semibold">{todo.title}</DialogTitle>
          </div>
          <DialogDescription className="sr-only">
            {t('insights.todoDetailsDescription', 'View complete details of the todo item')}
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[65vh] pr-2">
          <div className="space-y-5 pr-1">
            <section className="bg-muted/40 grid gap-4 rounded-lg border p-4 text-sm sm:grid-cols-2">
              {infoItems.map(({ label, value, Icon }) => (
                <div key={label} className="flex items-start gap-3">
                  <div className="bg-background text-muted-foreground flex h-9 w-9 items-center justify-center rounded-md border">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-xs tracking-wide uppercase">{label}</p>
                    <p className="text-foreground text-sm leading-tight font-medium">{value ?? '—'}</p>
                  </div>
                </div>
              ))}
            </section>

            {/* Description */}
            {todo.description && (
              <section className="bg-background/70 rounded-lg border p-4">
                <div className="flex items-center gap-2">
                  <Tag className="text-muted-foreground h-4 w-4" />
                  <h4 className="text-sm font-semibold">{t('insights.todoDescription', '详细描述')}</h4>
                </div>
                <p className="text-muted-foreground mt-2 text-sm leading-relaxed whitespace-pre-wrap">
                  {todo.description}
                </p>
              </section>
            )}

            {/* Keywords */}
            {todo.keywords && todo.keywords.length > 0 && (
              <section className="rounded-lg border p-4">
                <h4 className="mb-2 text-sm font-semibold">{t('insights.todoKeywords', '关键词')}</h4>
                <div className="flex flex-wrap gap-2">
                  {todo.keywords.map((keyword, idx) => (
                    <Badge key={idx} variant="secondary">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </section>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
