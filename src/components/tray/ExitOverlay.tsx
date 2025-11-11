/**
 * Exit Overlay
 *
 * Shows a full-screen overlay with loading indicator when app is exiting
 */

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listen } from '@tauri-apps/api/event'
import { Loader2 } from 'lucide-react'

export function ExitOverlay() {
  const { t } = useTranslation()
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    let unlisten: (() => void) | undefined

    // Listen for app-exit event (after user confirms)
    listen('app-exit', () => {
      console.log('[ExitOverlay] App is exiting, showing overlay')
      setIsExiting(true)
    })
      .then((unlistenFn) => {
        unlisten = unlistenFn
      })
      .catch((error) => {
        console.error('[ExitOverlay] Failed to setup listener:', error)
      })

    return () => {
      if (unlisten) {
        unlisten()
      }
    }
  }, [])

  if (!isExiting) {
    return null
  }

  return (
    <div
      className="bg-background/95 fixed inset-0 z-[9999] flex items-center justify-center backdrop-blur-sm"
      data-tauri-drag-region="false">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="text-primary size-12 animate-spin" />
        <div className="flex flex-col items-center gap-2">
          <h2 className="text-xl font-semibold">{t('tray.exitingTitle')}</h2>
          <p className="text-muted-foreground text-sm">{t('tray.exitingMessage')}</p>
        </div>
      </div>
    </div>
  )
}
