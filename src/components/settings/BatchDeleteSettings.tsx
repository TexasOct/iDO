import { useState } from 'react'
import DatePicker from 'react-datepicker'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import {
  deleteActivitiesByDate,
  deleteKnowledgeByDate,
  deleteTodosByDate,
  deleteDiariesByDate
} from '@/lib/client/apiClient'

interface BatchDeleteSettingsProps {
  className?: string
}

type DeleteByDateResponse = {
  success?: boolean
  message?: string
  error?: string
  data?: {
    deleted_count?: number
    deletedCount?: number
  }
}

export function BatchDeleteSettings({ className }: BatchDeleteSettingsProps) {
  const { t } = useTranslation()

  const [startDate, setStartDate] = useState<Date | null>(null)
  const [endDate, setEndDate] = useState<Date | null>(null)
  const [deleting, setDeleting] = useState(false)

  const isDateRangeValid = startDate && endDate && startDate <= endDate

  // 格式化日期为 YYYY-MM-DD
  const formatDate = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const handleBatchDelete = async (type: 'activities' | 'knowledge' | 'todos' | 'diaries') => {
    if (!isDateRangeValid) {
      toast.error(t('settings.invalidDateRange'))
      return
    }

    const typeNames = {
      activities: t('settings.deleteActivities').replace('删除 ', ''),
      knowledge: t('settings.deleteKnowledge').replace('删除 ', ''),
      todos: t('settings.deleteTodos').replace('删除 ', ''),
      diaries: t('settings.deleteDiaries').replace('删除 ', '')
    }

    const startDateStr = formatDate(startDate!)
    const endDateStr = formatDate(endDate!)

    if (
      !confirm(
        t('settings.confirmDelete', {
          start: startDateStr,
          end: endDateStr,
          type: typeNames[type]
        })
      )
    ) {
      return
    }

    setDeleting(true)
    try {
      const payload = { startDate: startDateStr, endDate: endDateStr }
      let result: DeleteByDateResponse | undefined
      switch (type) {
        case 'activities':
          result = (await deleteActivitiesByDate(payload)) as DeleteByDateResponse
          break
        case 'knowledge':
          result = (await deleteKnowledgeByDate(payload)) as DeleteByDateResponse
          break
        case 'todos':
          result = (await deleteTodosByDate(payload)) as DeleteByDateResponse
          break
        case 'diaries':
          result = (await deleteDiariesByDate(payload)) as DeleteByDateResponse
          break
      }

      if (result?.success) {
        const deletedCount = result.data?.deleted_count ?? result.data?.deletedCount
        toast.success(result.message || t('settings.deleteSuccess', { count: deletedCount }))
      } else {
        toast.error(result?.message || t('settings.deleteFailed'))
      }
    } catch (error) {
      console.error('Batch delete error:', error)
      toast.error(t('settings.deleteFailed') + ' - ' + t('settings.retry'))
    } finally {
      setDeleting(false)
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
              onClick={() => handleBatchDelete('activities')}
              disabled={!isDateRangeValid || deleting}
              className="w-full">
              {t('settings.deleteActivities')}
            </Button>
            <Button
              variant="destructive"
              onClick={() => handleBatchDelete('knowledge')}
              disabled={!isDateRangeValid || deleting}
              className="w-full">
              {t('settings.deleteKnowledge')}
            </Button>
            <Button
              variant="destructive"
              onClick={() => handleBatchDelete('todos')}
              disabled={!isDateRangeValid || deleting}
              className="w-full">
              {t('settings.deleteTodos')}
            </Button>
            <Button
              variant="destructive"
              onClick={() => handleBatchDelete('diaries')}
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
    </Card>
  )
}
