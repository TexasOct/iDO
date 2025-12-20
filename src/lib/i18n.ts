import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { resources } from '@/locales'

// Load the saved language from localStorage, otherwise use the browser language and default to zh-CN
const getInitialLanguage = (): string => {
  const savedLanguage = localStorage.getItem('language')
  if (savedLanguage) {
    return savedLanguage
  }

  // Detect the browser language (temporary until backend sync)
  const browserLanguage = navigator.language
  if (browserLanguage.startsWith('zh')) {
    return 'zh-CN'
  }
  return 'en'
}

i18n.use(initReactI18next).init({
  resources,
  lng: getInitialLanguage(),
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false // React already escapes values
  },
  react: {
    useSuspense: false
  }
})

// Persist language changes to localStorage
i18n.on('languageChanged', (lng) => {
  localStorage.setItem('language', lng)
})

/**
 * Sync frontend language with backend language setting
 * Should be called during app initialization
 */
export const syncLanguageWithBackend = async (backendLanguage: string): Promise<void> => {
  // Map backend language codes (zh, en) to frontend codes (zh-CN, en)
  const frontendLanguage = backendLanguage === 'zh' ? 'zh-CN' : 'en'

  // Only sync if no user preference exists in localStorage
  const savedLanguage = localStorage.getItem('language')
  if (!savedLanguage) {
    console.log(`[i18n] Syncing with backend language: ${backendLanguage} -> ${frontendLanguage}`)
    await i18n.changeLanguage(frontendLanguage)
    // This will be persisted to localStorage by the languageChanged event handler
  } else {
    console.log(`[i18n] Using saved language preference: ${savedLanguage}`)
  }
}

export default i18n
