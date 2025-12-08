import { useState, useMemo } from 'react'
import { Activity } from '@/lib/types/activity'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Loader2, Merge, Calendar, Clock } from 'lucide-react'
import { format } from 'date-fns'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { mergeActivitiesHandler } from '@/lib/client/apiClient'

interface MergeActivitiesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  activities: Activity[]
  onMergeSuccess?: () => void
}

export function MergeActivitiesDialog({ open, onOpenChange, activities, onMergeSuccess }: MergeActivitiesDialogProps) {
  const { t } = useTranslation()
  const [merging, setMerging] = useState(false)
  const [mergedTitle, setMergedTitle] = useState('')
  const [mergedDescription, setMergedDescription] = useState('')

  // Calculate merged time range and generate suggested title/description
  const mergedData = useMemo(() => {
    if (activities.length === 0) {
      return {
        startTime: 0,
        endTime: 0,
        suggestedTitle: '',
        suggestedDescription: ''
      }
    }

    // Sort by startTime
    const sorted = [...activities].sort((a, b) => a.startTime - b.startTime)
    const startTime = sorted[0].startTime
    const endTime = sorted[sorted.length - 1].endTime

    // Generate suggested title (use first activity's title)
    const suggestedTitle = sorted[0].title || t('activity.mergeTitle')

    // Generate suggested description (combine all descriptions)
    const descriptions = sorted
      .map((a) => a.description)
      .filter(Boolean)
      .join('\n\n')
    const suggestedDescription = descriptions || t('activity.mergedResultPreview')

    return {
      startTime,
      endTime,
      suggestedTitle,
      suggestedDescription
    }
  }, [activities, t])

  // Initialize suggested values when dialog opens
  useState(() => {
    if (open && !mergedTitle) {
      setMergedTitle(mergedData.suggestedTitle)
      setMergedDescription(mergedData.suggestedDescription)
    }
  })

  // Calculate total duration
  const totalDuration = useMemo(() => {
    const duration = mergedData.endTime - mergedData.startTime
    const hours = Math.floor(duration / (1000 * 60 * 60))
    const minutes = Math.floor((duration % (1000 * 60 * 60)) / (1000 * 60))
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }, [mergedData])

  const handleMerge = async () => {
    if (activities.length < 2) {
      toast.error(t('activity.mergeAtLeastTwo'))
      return
    }

    if (!mergedTitle.trim()) {
      toast.error(t('activity.mergeEnterTitle'))
      return
    }

    setMerging(true)

    try {
      const activityIds = activities.map((a) => a.id)

      // Call backend merge API using generated client
      const response = await mergeActivitiesHandler({
        activityIds,
        mergedTitle: mergedTitle.trim(),
        mergedDescription: mergedDescription.trim() || undefined
      })

      if (!response?.success) {
        console.error('[MergeActivitiesDialog] Merge failed:', response?.error)
        toast.error(t('activity.mergeFailed'))
        return
      }

      toast.success(t('activity.mergeSuccess', { count: activities.length }))
      onOpenChange(false)
      onMergeSuccess?.()
    } catch (error) {
      console.error('[MergeActivitiesDialog] Merge failed:', error)
      toast.error(t('activity.mergeFailed'))
    } finally {
      setMerging(false)
    }
  }

  const handleCancel = () => {
    if (merging) return
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Merge className="h-5 w-5" />
            {t('activity.mergeTitle')}
          </DialogTitle>
          <DialogDescription>{t('activity.mergeDescription', { count: activities.length })}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Activities to merge preview */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">
              {t('activity.activitiesToMerge', { count: activities.length })}
            </Label>
            <div className="border-border max-h-48 space-y-2 overflow-y-auto rounded-md border p-3">
              {activities.map((activity) => (
                <div key={activity.id} className="bg-muted/50 flex items-start gap-3 rounded-md p-2 text-sm">
                  <div className="flex-1">
                    <div className="text-foreground font-medium">{activity.title}</div>
                    {activity.description && (
                      <div className="text-muted-foreground mt-1 line-clamp-2 text-xs">{activity.description}</div>
                    )}
                    <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
                      <Clock className="h-3 w-3" />
                      <span>{format(new Date(activity.startTime), 'HH:mm:ss')}</span>
                      <span>-</span>
                      <span>{format(new Date(activity.endTime), 'HH:mm:ss')}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Merged activity preview */}
          <div className="border-primary/30 bg-primary/5 rounded-md border p-3">
            <div className="text-primary mb-2 flex items-center gap-2 text-xs font-semibold tracking-wider uppercase">
              <Calendar className="h-3 w-3" />
              {t('activity.mergedResultPreview')}
            </div>
            <div className="text-muted-foreground space-y-1 text-sm">
              <div className="flex items-center gap-2">
                <Clock className="h-3 w-3" />
                <span>
                  {format(new Date(mergedData.startTime), 'HH:mm:ss')} -{' '}
                  {format(new Date(mergedData.endTime), 'HH:mm:ss')}
                </span>
                <span className="text-xs">({totalDuration})</span>
              </div>
            </div>
          </div>

          {/* Input fields */}
          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="merged-title">{t('activity.mergedTitle')} *</Label>
              <Input
                id="merged-title"
                placeholder={t('activity.mergedTitlePlaceholder')}
                value={mergedTitle}
                onChange={(e) => setMergedTitle(e.target.value)}
                disabled={merging}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="merged-description">{t('activity.mergedDescription')}</Label>
              <Textarea
                id="merged-description"
                placeholder={t('activity.mergedDescriptionPlaceholder')}
                value={mergedDescription}
                onChange={(e) => setMergedDescription(e.target.value)}
                disabled={merging}
                rows={4}
                className="resize-none"
              />
            </div>
          </div>
        </div>

        <DialogFooter className="pt-4">
          <Button variant="outline" onClick={handleCancel} disabled={merging}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleMerge} disabled={merging || !mergedTitle.trim()}>
            {merging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('activity.mergeButton')} {activities.length} {t('activity.overview.activities')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
