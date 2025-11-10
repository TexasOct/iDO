import '@/styles/index.css'
import '@/lib/i18n'
import { Outlet } from 'react-router'
import { useEffect, useState } from 'react'

import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { ThemeProvider } from '@/components/system/theme/theme-provider'
import { Button } from '@/components/ui/button'
import { Toaster } from '@/components/ui/sonner'
import { useBackendLifecycle } from '@/hooks/useBackendLifecycle'
import { Titlebar } from '@/components/layout/Titlebar'
import { PermissionsGuide } from '@/components/permissions/PermissionsGuide'
import { useLive2dStore } from '@/lib/stores/live2d'
import { useFriendlyChat } from '@/hooks/useFriendlyChat'
import { isTauri } from '@/lib/utils/tauri'
import { syncLive2dWindow } from '@/lib/live2d/windowManager'
import { useSetupStore } from '@/lib/stores/setup'

function App() {
  const isWindowsUA = () => {
    try {
      if (typeof navigator === 'undefined') return false
      const ua = navigator.userAgent || ''
      const plat = (navigator as any).platform || ''
      const uaDataPlat = (navigator as any).userAgentData?.platform || ''
      const s = `${ua} ${plat} ${uaDataPlat}`.toLowerCase()
      return s.includes('win')
    } catch {
      return false
    }
  }

  const [isWindows, setIsWindows] = useState<boolean>(isWindowsUA())
  const [tauriReady, setTauriReady] = useState<boolean>(typeof window !== 'undefined' && '__TAURI__' in window)
  const { isTauriApp, status, errorMessage, retry } = useBackendLifecycle()
  const fetchLive2d = useLive2dStore((state) => state.fetch)

  // Setup flow state - used to hide global guides during initial setup
  const isSetupActive = useSetupStore((s) => s.isActive)
  const hasAcknowledged = useSetupStore((s) => s.hasAcknowledged)

  // Initialize friendly chat event listeners
  useFriendlyChat()

  // Detect platform quickly via UA and poll for Tauri readiness
  useEffect(() => {
    setIsWindows(isWindowsUA())
    if (tauriReady) return
    let tries = 0
    const id = setInterval(() => {
      tries += 1
      if (typeof window !== 'undefined' && '__TAURI__' in window) {
        setTauriReady(true)
        clearInterval(id)
      } else if (tries > 20) {
        clearInterval(id)
      }
    }, 50)
    return () => clearInterval(id)
  }, [tauriReady])

  useEffect(() => {
    if (!isTauriApp || status !== 'ready' || !isTauri()) {
      return
    }

    let cancelled = false

    const initializeLive2d = async () => {
      try {
        await fetchLive2d()
        if (cancelled) {
          return
        }
        const { state } = useLive2dStore.getState()
        await syncLive2dWindow(state.settings)
      } catch (error) {
        console.warn('[Live2D] init failed', error)
      }
    }

    void initializeLive2d()

    return () => {
      cancelled = true
    }
  }, [fetchLive2d, isTauriApp, status])

  const renderContent = () => {
    if (!isTauriApp || status === 'ready') {
      return <Outlet />
    }

    if (status === 'error') {
      return (
        <div className="flex h-full w-full flex-col items-center justify-center gap-4 px-6 text-center">
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">后台启动失败</h2>
            {errorMessage ? <p className="text-muted-foreground text-sm">{errorMessage}</p> : null}
          </div>
          <Button onClick={() => void retry()}>重新尝试</Button>
        </div>
      )
    }

    return <LoadingPage message="正在启动后台服务..." />
  }

  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <div
          className={`bg-background h-screen w-screen overflow-hidden ${
            isWindows ? 'rounded-2xl border border-black/10 shadow-xl dark:border-white/10' : ''
          }`}>
          {/* Global drag region for all platforms */}
          {tauriReady ? <Titlebar /> : null}
          {renderContent()}
          {/* Hide the PermissionsGuide while the initial setup overlay is active and not yet acknowledged */}
          {(!isSetupActive || hasAcknowledged) && <PermissionsGuide />}
          <Toaster
            position="top-right"
            theme="dark"
            richColors
            closeButton
            visibleToasts={3}
            duration={3000}
            expand={false}
          />
        </div>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export { App }
