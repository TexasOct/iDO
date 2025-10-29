import { Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface LoadingPageProps {
  message?: string
}

export function LoadingPage({ message }: LoadingPageProps) {
  const { t } = useTranslation()
  const displayMessage = message || t('common.loading')
  return (
    <div className="flex h-full w-full flex-col items-center justify-center">
      <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
      <p className="text-muted-foreground mt-4 text-sm">{displayMessage}</p>
    </div>
  )
}
