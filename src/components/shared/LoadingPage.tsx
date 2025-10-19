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
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      <p className="mt-4 text-sm text-muted-foreground">{displayMessage}</p>
    </div>
  )
}
