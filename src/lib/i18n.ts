import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { resources } from '@/locales'

// Load the saved language from localStorage, otherwise use the browser language and default to zh-CN
const getInitialLanguage = (): string => {
  const savedLanguage = localStorage.getItem('language')
  if (savedLanguage) {
    return savedLanguage
  }

  // Detect the browser language
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

export default i18n
