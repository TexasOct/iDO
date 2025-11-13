import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getVersion } from '@tauri-apps/api/app'
import { getCurrentWindow } from '@tauri-apps/api/window'
import appIcon from '../../src-tauri/icons/icon.png'

export default function About() {
  const { t } = useTranslation()
  const [version, setVersion] = useState<string>('0.1.0')
  const isWindows = useMemo(() => {
    try {
      if (typeof navigator === 'undefined') return false
      const ua = navigator.userAgent || ''
      const plat = (navigator as any).platform || ''
      const uaDataPlat = (navigator as any).userAgentData?.platform || ''
      const signature = `${ua} ${plat} ${uaDataPlat}`.toLowerCase()
      return signature.includes('win')
    } catch {
      return false
    }
  }, [])

  useEffect(() => {
    const loadVersion = async () => {
      try {
        const appVersion = await getVersion()
        setVersion(appVersion)
      } catch (error) {
        console.error('[About] Failed to get app version:', error)
      }
    }

    void loadVersion()
  }, [])

  const handleClose = async () => {
    const window = getCurrentWindow()
    await window.hide()
  }

  return (
    <div className="bg-background flex h-screen w-screen flex-col items-center justify-center overflow-hidden rounded-2xl border border-black/10 shadow-xl dark:border-white/10">
      {/* Custom titlebar (Windows still relies on native controls) */}
      <div
        data-tauri-drag-region="true"
        className="bg-background/80 absolute top-0 right-0 left-0 flex h-12 items-center justify-between border-b backdrop-blur-sm">
        {/* Left side - title */}
        <div className="pl-4">
          <div className="text-sm font-medium">{t('tray.about')}</div>
        </div>

        {/* Right side - custom close button (hidden on Windows to avoid duplicate titlebar controls) */}
        <div className="pr-4">
          {!isWindows && (
            <button
              onClick={handleClose}
              className="flex h-8 w-8 items-center justify-center rounded-md text-red-500 transition-colors hover:bg-red-500 hover:text-white"
              type="button">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round">
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col items-center gap-6 px-8 pt-16 pb-8 text-center">
        {/* App icon */}
        <div className="bg-primary/10 flex h-24 w-24 items-center justify-center overflow-hidden rounded-2xl">
          <img src={appIcon} alt="iDO Logo" className="h-full w-full object-contain" />
        </div>

        {/* App name and version */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">iDO</h1>
          <p className="text-muted-foreground text-sm">{t('tray.version', { version })}</p>
        </div>

        {/* Description */}
        <p className="text-muted-foreground max-w-sm text-sm leading-relaxed">
          {t('about.description', {
            defaultValue: 'AI-powered desktop activity monitoring and task recommendation system'
          })}
        </p>

        {/* Additional info */}
        <div className="text-muted-foreground space-y-1 text-xs">
          <p>&copy; 2025 iDO</p>
          <p>{t('about.allRightsReserved', { defaultValue: 'All rights reserved' })}</p>
        </div>
      </div>
    </div>
  )
}
