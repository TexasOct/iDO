import * as React from 'react'
import { format } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'
import { CalendarIcon } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

interface DatePickerProps {
  date?: Date
  value?: string // YYYY-MM-DD format (alternative to date)
  onDateChange?: (date: Date | undefined) => void
  onChange?: (date: string) => void // YYYY-MM-DD format (alternative to onDateChange)
  placeholder?: string
  disabled?: boolean
  maxDate?: Date
  minDate?: Date
  buttonSize?: React.ComponentProps<typeof Button>['size']
  locale?: string
  className?: string
  fullWidth?: boolean
}

export function DatePicker({
  date,
  value,
  onDateChange,
  onChange,
  placeholder = 'Pick a date',
  disabled = false,
  maxDate,
  minDate,
  buttonSize = 'default',
  locale: localeProp,
  className,
  fullWidth = true
}: DatePickerProps) {
  const { i18n } = useTranslation()
  const [open, setOpen] = React.useState(false)

  // Support both Date object and string format
  const selectedDate = React.useMemo(() => {
    if (date) return date
    if (value) return new Date(value)
    return undefined
  }, [date, value])

  // Determine locale for date-fns
  const activeLocale = React.useMemo(() => localeProp ?? i18n.language ?? 'en', [i18n.language, localeProp])
  const dateLocale = React.useMemo(() => (activeLocale.startsWith('zh') ? zhCN : enUS), [activeLocale])

  // Disable dates based on maxDate and minDate
  const disabledDatesPredicate = React.useCallback(
    (checkDate: Date) => {
      const checkTime = new Date(checkDate)
      checkTime.setHours(0, 0, 0, 0)

      if (maxDate) {
        const maxTime = new Date(maxDate)
        maxTime.setHours(0, 0, 0, 0)
        if (checkTime > maxTime) return true
      }

      if (minDate) {
        const minTime = new Date(minDate)
        minTime.setHours(0, 0, 0, 0)
        if (checkTime < minTime) return true
      }

      return false
    },
    [maxDate, minDate]
  )

  const handleSelect = React.useCallback(
    (newDate: Date | undefined) => {
      if (newDate) {
        // Call Date-based callback if provided
        onDateChange?.(newDate)

        // Call string-based callback if provided
        if (onChange) {
          const year = newDate.getFullYear()
          const month = String(newDate.getMonth() + 1).padStart(2, '0')
          const day = String(newDate.getDate()).padStart(2, '0')
          const formatted = `${year}-${month}-${day}`
          onChange(formatted)
        }
      }
      setOpen(false)
    },
    [onDateChange, onChange]
  )

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size={buttonSize}
          className={cn(
            `${fullWidth ? 'w-full' : 'w-auto'} justify-start text-left font-normal`,
            !selectedDate && 'text-muted-foreground',
            className
          )}
          disabled={disabled}>
          <CalendarIcon className="mr-2 size-4" />
          {selectedDate ? format(selectedDate, 'PPP', { locale: dateLocale }) : <span>{placeholder}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selectedDate}
          onSelect={handleSelect}
          disabled={minDate || maxDate ? disabledDatesPredicate : undefined}
          initialFocus
          locale={dateLocale}
        />
      </PopoverContent>
    </Popover>
  )
}
