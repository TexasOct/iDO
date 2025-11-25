import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Clock } from 'lucide-react'

interface RecurrenceRule {
  type: 'daily' | 'weekly' | 'monthly' | 'none'
  interval?: number
}

interface TimeRangeEditorProps {
  startTime?: string // HH:MM format
  endTime?: string // HH:MM format
  recurrenceRule?: RecurrenceRule
  onStartTimeChange: (time: string) => void
  onEndTimeChange: (time: string) => void
  onRecurrenceChange: (rule: RecurrenceRule) => void
}

export function TimeRangeEditor({
  startTime = '09:00',
  endTime,
  recurrenceRule = { type: 'none' },
  onStartTimeChange,
  onEndTimeChange,
  onRecurrenceChange
}: TimeRangeEditorProps) {
  const { t } = useTranslation()

  // Helper function to calculate end time (1 hour after start time)
  const calculateEndTime = (start: string): string => {
    const [hours, minutes] = start.split(':').map(Number)
    const endHour = (hours + 1) % 24
    return `${String(endHour).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
  }

  const handleStartTimeChange = (newStartTime: string) => {
    onStartTimeChange(newStartTime)
    // If no end time is set, automatically set it to 1 hour after start time
    if (!endTime || !endTime.trim()) {
      onEndTimeChange(calculateEndTime(newStartTime))
    }
  }

  const handleRecurrenceTypeChange = (type: string) => {
    onRecurrenceChange({
      type: type as RecurrenceRule['type'],
      interval: type === 'none' ? undefined : 1
    })
  }

  return (
    <div className="space-y-4">
      {/* Time Range Section */}
      <div className="space-y-3">
        <Label className="flex items-center gap-2 text-sm font-medium">
          <Clock className="size-4" />
          {t('insights.timeRange')}
        </Label>

        <div className="grid grid-cols-2 gap-3">
          {/* Start Time */}
          <div className="space-y-2">
            <Label className="text-muted-foreground text-xs">{t('insights.startTime')}</Label>
            <Input
              type="time"
              value={startTime}
              onChange={(e) => handleStartTimeChange(e.target.value)}
              className="font-mono"
            />
          </div>

          {/* End Time */}
          <div className="space-y-2">
            <Label className="text-muted-foreground text-xs">{t('insights.endTime')}</Label>
            <Input
              type="time"
              value={endTime || ''}
              onChange={(e) => onEndTimeChange(e.target.value)}
              className="font-mono"
              placeholder="--:--"
            />
          </div>
        </div>

        {endTime && (
          <p className="text-muted-foreground text-xs">
            {t('insights.duration')}: {calculateDuration(startTime, endTime)}
          </p>
        )}
      </div>

      {/* Recurrence Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium">{t('insights.repeatTodo')}</Label>
          <Switch
            checked={recurrenceRule.type !== 'none'}
            onCheckedChange={(checked) => {
              if (checked) {
                onRecurrenceChange({ type: 'daily', interval: 1 })
              } else {
                onRecurrenceChange({ type: 'none' })
              }
            }}
          />
        </div>

        {recurrenceRule.type !== 'none' && (
          <Select value={recurrenceRule.type || 'daily'} onValueChange={handleRecurrenceTypeChange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">{t('insights.recurrence.daily')}</SelectItem>
              <SelectItem value="weekly">{t('insights.recurrence.weekly')}</SelectItem>
              <SelectItem value="monthly">{t('insights.recurrence.monthly')}</SelectItem>
            </SelectContent>
          </Select>
        )}

        {recurrenceRule.type !== 'none' && (
          <p className="text-muted-foreground text-xs">{getRecurrenceDescription(recurrenceRule, t)}</p>
        )}
      </div>
    </div>
  )
}

// Helper function to calculate duration between two times
function calculateDuration(start: string, end: string): string {
  const [startHour, startMin] = start.split(':').map(Number)
  const [endHour, endMin] = end.split(':').map(Number)

  const startMinutes = startHour * 60 + startMin
  const endMinutes = endHour * 60 + endMin

  let diff = endMinutes - startMinutes
  if (diff < 0) {
    diff += 24 * 60 // Handle cross-midnight
  }

  const hours = Math.floor(diff / 60)
  const minutes = diff % 60

  if (hours === 0) {
    return `${minutes} min`
  } else if (minutes === 0) {
    return `${hours} h`
  } else {
    return `${hours} h ${minutes} min`
  }
}

// Helper function to get recurrence description
function getRecurrenceDescription(rule: RecurrenceRule, t: any): string {
  switch (rule.type) {
    case 'daily':
      return t('insights.recurrence.dailyDesc')
    case 'weekly':
      return t('insights.recurrence.weeklyDesc')
    case 'monthly':
      return t('insights.recurrence.monthlyDesc')
    default:
      return ''
  }
}
