# 国际化 (i18n) 指南

本文档描述 Rewind 项目的 i18n（国际化）策略、文件位置、添加/修改翻译的步骤、验证命令以及常见注意事项。项目采用「TypeScript-first」的翻译方案 —— 英文文件作为源（source of truth），并通过类型校验、验证脚本保证其它语言的一致性。

---

## 关键点速览

- 英文翻译文件为源文件，位于：`src/locales/en.ts`
- 其他语言文件（例如中文）需保持与英文相同的 key 结构：`src/locales/zh-CN.ts`
- 使用 `pnpm check-i18n` 校验各语言文件的一致性（CI 中应作为必过项）
- 前端组件通过类型安全的翻译函数或 hook 使用翻译 key，例如 `t('myFeature.title')`

---

## 文件位置（示例）

- English (source of truth)
```Rewind/src/locales/en.ts#L1-20
export const en = {
  common: {
    save: 'Save',
    cancel: 'Cancel',
  },
  myFeature: {
    title: 'Feature Title',
    description: 'Short description of the feature.'
  }
} as const
```

- Chinese (must mirror `en.ts` 的 key 结构)
```Rewind/src/locales/zh-CN.ts#L1-20
export const zhCN = {
  common: {
    save: '保存',
    cancel: '取消',
  },
  myFeature: {
    title: '功能标题',
    description: '功能的简短描述。'
  }
} as const
```

---

## 添加 / 修改 翻译 — 推荐流程

1. 在 `src/locales/en.ts` 添加或更新 key（英语为主源）。
2. 在对应语言文件（例如 `src/locales/zh-CN.ts`）添加相同的键路径并翻译。
3. 本地运行翻译校验：
```/dev/null/commands.sh#L1-3
pnpm check-i18n
# 若新增了后端 Pydantic → TS 类型变动，需重新生成相关类型（或按项目流程）
```
4. 提交变更并在 PR 中注明你更新了哪些翻译键，方便审阅。

---

## 在组件中使用翻译

项目中应使用已有的翻译 hook / 工具（示例）：

```Rewind/src/views/SomeView/index.tsx#L1-12
import { useTranslation } from '@/lib/i18n'

export default function SomeView() {
  const { t } = useTranslation()
  return (
    <div>
      <h1>{t('myFeature.title')}</h1>
      <p>{t('myFeature.description')}</p>
      <button>{t('common.save')}</button>
    </div>
  )
}
```

注意：总是使用 key（字符串）而非硬编码文本，以保持可切换和可检测。

---

## 验证与 CI 建议

- 将 `pnpm check-i18n` 集成到 CI（例如 PR 校验流程），确保新增/修改的 key 在所有语言文件中都有对应条目。
- 在 PR 模板或提交说明中提醒译者或审阅者：新增 key 需要同步添加到所有目标语言。
- 如果需要自动化翻译占位（例如先占位英文），可在 PR 中添加 TODO 注释，并创建 issue 指派翻译任务。

---

## 常见问题与注意事项

- 必须以 `src/locales/en.ts` 为准：不要直接在其他语言文件中增加英文 key 并认为已完成。
- 保持 key 结构稳定：重命名 key 会引发大量连锁修改，尽量新增新 key，必要时同时做重命名迁移说明。
- 避免在翻译值中嵌入不可控 HTML 或富文本 —— 若需要富文本，使用占位符并在渲染端做好安全处理。
- 在组件内拼接翻译字符串会破坏国际化（例如：`t('items') + ' ' + count`），优先使用参数化字符串或占位符：
```Rewind/src/locales/en.ts#L21-30
export const en = {
  notifications: {
    itemCount: 'You have {count} items'
  }
} as const
```
并在使用处传入参数。

---

## 翻译最佳实践（简要）

- 小团队：在 PR 描述中列出新增或变更的翻译 keys，方便 reviewer 检查。
- 大平台 / 多语言：把 `en.ts` 视为稳定接口，变更前与产品/设计团队沟通。
- 使用短、上下文明确的 key 路径（例如：`settings.profile.saveButton`），而不是模糊的 `save1`、`save2`。

---

如果你需要，我可以继续帮你：

- 生成一个简单的 `pnpm check-i18n` 的实现示例脚本（用于 docs），或者
- 撰写 `docs/i18n.md` 的英文版概要，方便外部贡献者阅读。
