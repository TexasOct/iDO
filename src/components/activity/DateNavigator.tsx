import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { format, isToday, type Locale } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'

interface DateNavigatorProps {
  currentDate: Date
  onPrevious: () => void
  onNext: () => void
}

const localeMap: Record<string, Locale> = {
  zh: zhCN,
  'zh-CN': zhCN,
  en: enUS,
  'en-US': enUS
}

/**
 * Date navigation component with previous/next arrows
 * Displays the current date with "Today" indicator
 */
export function DateNavigator({ currentDate, onPrevious, onNext }: DateNavigatorProps) {
  const { t, i18n } = useTranslation()
  const locale = localeMap[i18n.language] ?? enUS
  const isTodayDate = isToday(currentDate)

  const dateDisplay = isTodayDate
    ? `${t('activity.today')}, ${format(currentDate, 'MMM d', { locale })}`
    : format(currentDate, 'PPP', { locale })

  return (
    <div className="flex items-center gap-3">
      <Button variant="ghost" size="icon" onClick={onPrevious} className="h-8 w-8">
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <h1 className="text-2xl font-semibold">{dateDisplay}</h1>
      <Button variant="ghost" size="icon" onClick={onNext} className="h-8 w-8">
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  )
}
