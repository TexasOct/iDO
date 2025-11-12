import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { useTranslation } from 'react-i18next'
import type { MonitorInfo, ScreenSetting } from '@/lib/types/settings'

interface ScreenCardProps {
  monitor: MonitorInfo
  setting: ScreenSetting | undefined
  preview: string | undefined
  onToggle: (monitorIndex: number, enabled: boolean) => void
  isLoadingPreview?: boolean
}

export function ScreenCard({ monitor, setting, preview, onToggle, isLoadingPreview = false }: ScreenCardProps) {
  const { t } = useTranslation()
  const isEnabled = setting?.is_enabled ?? monitor.is_primary

  return (
    <div className="group bg-background/70 hover:border-primary/40 relative overflow-hidden rounded-xl border shadow-sm transition-colors">
      <div className="flex flex-col gap-4 p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <span>{monitor.name}</span>
              {monitor.is_primary && <Badge variant="secondary">{t('settings.primaryScreen')}</Badge>}
            </div>
            <div className="text-muted-foreground flex flex-wrap gap-2 text-xs">
              <span className="bg-muted/70 rounded-full px-2 py-0.5">
                {t('settings.resolution')}: {monitor.resolution}
              </span>
              <span className="bg-muted/70 rounded-full px-2 py-0.5">
                {t('settings.position')}: ({monitor.left}, {monitor.top})
              </span>
            </div>
          </div>
          <Switch checked={isEnabled} onCheckedChange={(checked: boolean) => onToggle(monitor.index, checked)} />
        </div>
        <div className="bg-muted/40 relative overflow-hidden rounded-lg border">
          <div className="from-muted/50 to-background flex aspect-[16/9] w-full items-center justify-center bg-gradient-to-br">
            {preview ? (
              <img
                src={`data:image/jpeg;base64,${preview}`}
                alt={`${monitor.name} preview`}
                className="h-full w-full object-contain"
              />
            ) : isLoadingPreview ? (
              <div className="text-muted-foreground text-center text-sm">
                <div className="animate-pulse">{t('common.loading')}</div>
                <div className="mt-1 text-xs">
                  {monitor.name} · {monitor.resolution}
                </div>
              </div>
            ) : (
              <div className="text-muted-foreground text-center text-sm">
                <div>{t('settings.previewWillAppear')}</div>
                <div className="mt-1 text-xs">
                  {monitor.name} · {monitor.resolution}
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="text-muted-foreground flex items-center justify-between text-xs">
          <span>{t('settings.displaySelectionHint')}</span>
          <span className="font-medium">
            {isEnabled ? t('settings.captureEnabled') : t('settings.captureDisabled')}
          </span>
        </div>
      </div>
    </div>
  )
}
