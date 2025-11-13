import { useState } from 'react'
import DatePicker from 'react-datepicker'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import {
  deleteActivitiesByDate,
  deleteKnowledgeByDate,
  deleteTodosByDate,
  deleteDiariesByDate
} from '@/lib/client/apiClient'

interface BatchDeleteSettingsProps {
  className?: string
}

type DeleteType = 'activities' | 'knowledge' | 'todos' | 'diaries'

type DeleteByDatePayload = {
  startDate: string
  endDate: string
}

type DeleteByDateCommand = (payload: DeleteByDatePayload) => Promise<unknown>

const deleteTypeTranslationKeys = {
  activities: 'settings.deleteActivities',
  knowledge: 'settings.deleteKnowledge',
  todos: 'settings.deleteTodos',
  diaries: 'settings.deleteDiaries'
} as const satisfies Record<DeleteType, string>

const deleteCommands: Record<DeleteType, DeleteByDateCommand> = {
  activities: deleteActivitiesByDate,
  knowledge: deleteKnowledgeByDate,
  todos: deleteTodosByDate,
  diaries: deleteDiariesByDate
}

interface DeleteOperationResult {
  success: boolean
  message?: string
  deletedCount?: number
}

const normalizeDeleteResult = (raw: unknown): DeleteOperationResult => {
  if (!raw || typeof raw !== 'object') {
    return { success: false }
  }

  const record = raw as Record<string, unknown>
  const data =
    typeof record.data === 'object' && record.data !== null ? (record.data as Record<string, unknown>) : undefined

  const snakeDeletedCount = data?.['deleted_count']
  const camelDeletedCount = data?.['deletedCount']

  return {
    success: record.success === true,
    message: typeof record.message === 'string' ? record.message : undefined,
    deletedCount:
      typeof snakeDeletedCount === 'number'
        ? snakeDeletedCount
        : typeof camelDeletedCount === 'number'
          ? camelDeletedCount
          : undefined
  }
}

const cleanDeleteTypeLabel = (label: string): string => {
  const normalized = label.replace(/^(?:删除|Delete)\s*/i, '').trim()
  return normalized || label
}

export function BatchDeleteSettings({ className }: BatchDeleteSettingsProps) {
  const { t } = useTranslation()

  const [startDate, setStartDate] = useState<Date | null>(null)
  const [endDate, setEndDate] = useState<Date | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleteType, setDeleteType] = useState<DeleteType | null>(null)

  const getDeleteTypeLabel = (type: DeleteType) => cleanDeleteTypeLabel(String(t(deleteTypeTranslationKeys[type])))

  const isDateRangeValid = startDate && endDate && startDate <= endDate

  // 格式化日期为 YYYY-MM-DD
  const formatDate = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  // 显示确认对话框
  const showConfirmDialog = (type: DeleteType) => {
    setDeleteType(type)
    setConfirmOpen(true)
  }

  // 执行删除操作
  const handleConfirmDelete = async () => {
    if (!deleteType || !startDate || !endDate) return

    setDeleting(true)
    setConfirmOpen(false)

    try {
      const startDateStr = formatDate(startDate)
      const endDateStr = formatDate(endDate)

      const payload = { startDate: startDateStr, endDate: endDateStr }
      const deleteCommand = deleteCommands[deleteType]
      const result = normalizeDeleteResult(await deleteCommand(payload))

      if (result.success) {
        toast.success(result.message || t('settings.deleteSuccess', { count: result.deletedCount ?? 0 }))
      } else {
        toast.error(result.message || t('settings.deleteFailed'))
      }
    } catch (error) {
      console.error('Batch delete error:', error)
      toast.error(t('settings.deleteFailed') + ' - ' + t('settings.retry'))
    } finally {
      setDeleting(false)
      setDeleteType(null)
    }
  }

  const today = new Date()
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{t('settings.batchDelete')}</CardTitle>
        <CardDescription>{t('settings.batchDeleteDescription')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 日期选择 */}
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('settings.startDate')}</Label>
              <DatePicker
                selected={startDate}
                onChange={(date) => setStartDate(date)}
                maxDate={today}
                dateFormat="yyyy/MM/dd"
                placeholderText="YYYY/MM/DD"
                className="border-input placeholder:text-muted-foreground focus-visible:ring-ring flex h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:ring-1 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            <div className="space-y-2">
              <Label>{t('settings.endDate')}</Label>
              <DatePicker
                selected={endDate}
                onChange={(date) => setEndDate(date)}
                maxDate={today}
                dateFormat="yyyy/MM/dd"
                placeholderText="YYYY/MM/DD"
                className="border-input placeholder:text-muted-foreground focus-visible:ring-ring flex h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:ring-1 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setStartDate(thirtyDaysAgo)
                setEndDate(today)
              }}>
              {t('settings.last30Days')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
                setStartDate(sevenDaysAgo)
                setEndDate(today)
              }}>
              {t('settings.last7Days')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000)
                setStartDate(yesterday)
                setEndDate(yesterday)
              }}>
              {t('settings.yesterday')}
            </Button>
          </div>
        </div>

        {/* 批量删除按钮 */}
        <div className="space-y-4 border-t pt-4">
          <Label className="text-base font-semibold">{t('settings.selectDataType')}</Label>
          <p className="text-muted-foreground text-sm">
            {t('settings.willDeleteBetween', {
              start: startDate ? formatDate(startDate) : 'YYYY/MM/DD',
              end: endDate ? formatDate(endDate) : 'YYYY/MM/DD'
            })}
          </p>

          <div className="grid grid-cols-2 gap-4">
            <Button
              variant="destructive"
              onClick={() => showConfirmDialog('activities')}
              disabled={!isDateRangeValid || deleting}
              className="w-full">
              {t('settings.deleteActivities')}
            </Button>
            <Button
              variant="destructive"
              onClick={() => showConfirmDialog('knowledge')}
              disabled={!isDateRangeValid || deleting}
              className="w-full">
              {t('settings.deleteKnowledge')}
            </Button>
            <Button
              variant="destructive"
              onClick={() => showConfirmDialog('todos')}
              disabled={!isDateRangeValid || deleting}
              className="w-full">
              {t('settings.deleteTodos')}
            </Button>
            <Button
              variant="destructive"
              onClick={() => showConfirmDialog('diaries')}
              disabled={!isDateRangeValid || deleting}
              className="w-full">
              {t('settings.deleteDiaries')}
            </Button>
          </div>
        </div>

        {/* 警告信息 */}
        <div className="bg-destructive/10 border-destructive/20 rounded-md border p-4">
          <p className="text-destructive text-sm font-medium">{t('settings.warning')}</p>
          <p className="text-muted-foreground mt-1 text-sm">{t('settings.batchDeleteWarning')}</p>
        </div>
      </CardContent>

      {/* 确认对话框 */}
      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-destructive flex items-center gap-2">
              ⚠️ {t('settings.warning')}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-base">
              {deleteType &&
                startDate &&
                endDate &&
                t('settings.confirmDelete', {
                  start: formatDate(startDate),
                  end: formatDate(endDate),
                  type: getDeleteTypeLabel(deleteType)
                })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteType(null)}>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDelete} className="bg-destructive hover:bg-destructive/90">
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}
