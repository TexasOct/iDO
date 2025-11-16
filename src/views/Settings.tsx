import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import ModelManagement from '@/components/models/ModelManagement'
import { Live2dSettings } from '@/components/settings/Live2dSettings'
import { FriendlyChatSettings } from '@/components/settings/FriendlyChatSettings'
import { DatabaseSettings } from '@/components/settings/DatabaseSettings'
import { ScreenshotSettings } from '@/components/settings/ScreenshotSettings'
import { ScreenSelectionSettings } from '@/components/settings/ScreenSelectionSettings'
import { PerceptionSettings } from '@/components/settings/PerceptionSettings'
import { AppearanceSettings } from '@/components/settings/AppearanceSettings'
import { PermissionsSettings } from '@/components/settings/PermissionsSettings'
import { BatchDeleteSettings } from '@/components/settings/BatchDeleteSettings'
import { DeveloperSettings } from '@/components/settings/DeveloperSettings'
import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { cn } from '@/lib/utils'

export default function SettingsView() {
  const { t } = useTranslation()
  const categories = useMemo(() => {
    const groups = [
      {
        id: 'experience',
        title: t('settings.categories.experience.title'),
        description: t('settings.categories.experience.description'),
        sections: [
          <AppearanceSettings key="appearance" />,
          <FriendlyChatSettings key="friendly-chat" />,
          <Live2dSettings key="live2d" />
        ]
      },
      {
        id: 'permissions',
        title: t('settings.categories.permissions.title'),
        description: t('settings.categories.permissions.description'),
        sections: [
          <PermissionsSettings key="permissions" />,
          <ScreenshotSettings key="screenshot" />,
          <ScreenSelectionSettings key="screen-selection" />
        ]
      },
      {
        id: 'perception',
        title: t('settings.categories.perception.title'),
        description: t('settings.categories.perception.description'),
        sections: [<PerceptionSettings key="perception" />]
      },
      {
        id: 'models',
        title: t('settings.categories.models.title'),
        description: t('settings.categories.models.description'),
        sections: [<ModelManagement key="models" />]
      },
      {
        id: 'data',
        title: t('settings.categories.data.title'),
        description: t('settings.categories.data.description'),
        sections: [<DatabaseSettings key="database" />, <BatchDeleteSettings key="batch-delete" />]
      }
    ]

    if (import.meta.env.DEV) {
      groups.push({
        id: 'developer',
        title: t('settings.categories.developer.title'),
        description: t('settings.categories.developer.description'),
        sections: [<DeveloperSettings key="developer" />]
      })
    }

    return groups
  }, [t])
  const [activeCategory, setActiveCategory] = useState(() => (categories[0]?.id ? categories[0].id : ''))
  const activeCategoryData = useMemo(
    () => categories.find((category) => category.id === activeCategory) ?? categories[0],
    [categories, activeCategory]
  )

  return (
    <PageLayout>
      <PageHeader title={t('settings.title')} description={t('settings.description')} />

      <div className="flex flex-1 flex-col gap-6 overflow-hidden px-6">
        <div className="flex h-full w-full max-w-6xl gap-6">
          <nav className="contents w-48 shrink-0 sm:block lg:block">
            <div className="bg-card/70 sticky">
              <div className="flex flex-col gap-1">
                {categories.map((category) => {
                  const isActive = activeCategory === category.id
                  return (
                    <button
                      key={category.id}
                      type="button"
                      onClick={() => setActiveCategory(category.id)}
                      className={cn(
                        'relative w-full rounded-xl py-2 pr-4 pl-5 text-left text-sm transition-colors',
                        'focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none',
                        'hover:text-foreground',
                        isActive ? 'bg-background text-foreground' : 'text-muted-foreground'
                      )}>
                      <span className="font-medium">{category.title}</span>
                      {isActive && (
                        <span className="bg-primary absolute inset-y-2 left-2 w-0.5 rounded-full" aria-hidden />
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          </nav>

          <div className="flex-1 overflow-y-auto pb-10">
            {activeCategoryData && (
              <section key={activeCategoryData.id} className="bg-background/70 p-5 pt-0 backdrop-blur">
                <div className="settings-section">
                  {activeCategoryData.sections.map((section, index) => (
                    <div key={index} className="py-4 first:pt-0 last:pb-0">
                      {section}
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  )
}
