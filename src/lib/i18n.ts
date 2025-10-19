import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { resources } from '@/locales'

// 从 localStorage 获取保存的语言，如果没有则使用浏览器语言或默认为中文
const getInitialLanguage = (): string => {
  const savedLanguage = localStorage.getItem('language')
  if (savedLanguage) {
    return savedLanguage
  }

  // 检测浏览器语言
  const browserLanguage = navigator.language
  if (browserLanguage.startsWith('zh')) {
    return 'zh-CN'
  }
  return 'en'
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: getInitialLanguage(),
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    react: {
      useSuspense: false,
    },
  })

// 监听语言变化，保存到 localStorage
i18n.on('languageChanged', (lng) => {
  localStorage.setItem('language', lng)
})

export default i18n
