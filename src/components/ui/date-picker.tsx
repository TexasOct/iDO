import * as React from 'react'
import { format } from 'date-fns'
import { ChevronDown } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

interface DatePickerProps {
  date?: Date
  onDateChange: (date: Date | undefined) => void
  placeholder?: string
  disabled?: boolean
  maxDate?: Date
  buttonSize?: React.ComponentProps<typeof Button>['size']
}

export function DatePicker({
  date,
  onDateChange,
  placeholder = 'Pick a date',
  disabled = false,
  maxDate,
  buttonSize = 'default'
}: DatePickerProps) {
  const [open, setOpen] = React.useState(false)

  // 获取当前日期（忽略时间部分）
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // 使用传入的 maxDate 或默认为今天
  const effectiveMaxDate = maxDate ? new Date(maxDate) : today
  effectiveMaxDate.setHours(23, 59, 59, 999)

  // 禁用超过 maxDate 的日期
  const disabledDatesPredicate = (checkDate: Date) => {
    const checkTime = new Date(checkDate)
    checkTime.setHours(0, 0, 0, 0)
    const maxTime = new Date(effectiveMaxDate)
    maxTime.setHours(0, 0, 0, 0)
    return checkTime > maxTime
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size={buttonSize}
          className={cn('justify-between pr-3 font-normal', !date && 'text-muted-foreground')}
          disabled={disabled}>
          <span className="text-sm">{date ? format(date, 'yyyy-MM-dd') : placeholder}</span>
          <ChevronDown className="ml-2 h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={date}
          onSelect={(selectedDate) => {
            onDateChange(selectedDate)
            setOpen(false)
          }}
          disabled={disabledDatesPredicate}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  )
}
