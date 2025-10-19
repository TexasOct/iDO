import { Globe } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { useTranslation } from 'react-i18next'
import { useSettingsStore } from '@/lib/stores/settings'
import { languages } from '@/locales'

export function LanguageToggle() {
  const { i18n, t } = useTranslation()
  const { updateLanguage } = useSettingsStore()

  const handleLanguageChange = (languageCode: string) => {
    i18n.changeLanguage(languageCode)
    updateLanguage(languageCode as 'zh-CN' | 'en-US')
  }

  const currentLanguage = languages.find((lang) => lang.code === i18n.language)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" title={currentLanguage?.name || t('common.language')}>
          <Globe className="h-[1.2rem] w-[1.2rem]" />
          <span className="sr-only">{t('common.toggleLanguage')}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {languages.map((lang) => (
          <DropdownMenuItem
            key={lang.code}
            onClick={() => handleLanguageChange(lang.code)}
            className={i18n.language === lang.code ? 'bg-accent' : ''}
          >
            {lang.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
