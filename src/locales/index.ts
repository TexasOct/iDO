import { en } from './en'
import { zhCN } from './zh-CN'

export const resources = {
  en: {
    translation: en
  },
  'zh-CN': {
    translation: zhCN
  }
} as const

export const languages = [
  { code: 'en', name: 'English' },
  { code: 'zh-CN', name: '简体中文' }
] as const

export type Language = (typeof languages)[number]['code']
