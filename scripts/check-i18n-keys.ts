/**
 * 验证所有语言文件的 key 是否一致
 * 确保每个语言都包含相同的翻译 key
 */

import { en } from '../src/locales/en'
import { zhCN } from '../src/locales/zh-CN'

type NestedKeys<T> = T extends object
  ? {
      [K in keyof T]: K extends string ? `${K}` | `${K}.${NestedKeys<T[K]>}` : never
    }[keyof T]
  : never

type TranslationKeys = NestedKeys<typeof en>

function getAllKeys(obj: any, prefix = ''): string[] {
  const keys: string[] = []

  for (const key in obj) {
    const fullKey = prefix ? `${prefix}.${key}` : key
    if (typeof obj[key] === 'object' && obj[key] !== null) {
      keys.push(...getAllKeys(obj[key], fullKey))
    } else {
      keys.push(fullKey)
    }
  }

  return keys
}

function checkTranslationKeys() {
  const enKeys = getAllKeys(en).sort()
  const zhCNKeys = getAllKeys(zhCN).sort()

  console.log('🔍 Checking translation keys consistency...\n')

  // 检查 key 数量
  console.log(`English keys: ${enKeys.length}`)
  console.log(`Chinese keys: ${zhCNKeys.length}\n`)

  // 检查缺失的 key
  const missingInZhCN = enKeys.filter((key) => !zhCNKeys.includes(key))
  const missingInEn = zhCNKeys.filter((key) => !enKeys.includes(key))

  let hasErrors = false

  if (missingInZhCN.length > 0) {
    hasErrors = true
    console.error('❌ Keys missing in zh-CN:')
    missingInZhCN.forEach((key) => console.error(`   - ${key}`))
    console.log('')
  }

  if (missingInEn.length > 0) {
    hasErrors = true
    console.error('❌ Keys missing in en:')
    missingInEn.forEach((key) => console.error(`   - ${key}`))
    console.log('')
  }

  if (!hasErrors) {
    console.log('✅ All translation keys are consistent!')
  } else {
    console.error('❌ Translation keys are inconsistent!')
    process.exit(1)
  }
}

checkTranslationKeys()
