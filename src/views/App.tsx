import '@/styles/index.css'
import '@/lib/i18n'
import { Outlet } from 'react-router'
import { useEffect } from 'react'

import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { ThemeProvider } from '@/components/system/theme/theme-provider'
import { Button } from '@/components/ui/button'
import { Toaster } from '@/components/ui/sonner'
import { useBackendLifecycle } from '@/hooks/useBackendLifecycle'
import { DragRegion } from '@/components/layout/DragRegion'
import { PermissionsGuide } from '@/components/permissions/PermissionsGuide'
import { useLive2dStore } from '@/lib/stores/live2d'
import { isTauri } from '@/lib/utils/tauri'

function App() {
  const { isTauriApp, status, errorMessage, retry } = useBackendLifecycle()
  const fetchLive2d = useLive2dStore((state) => state.fetch)

  useEffect(() => {
    if (!isTauri()) return
    fetchLive2d().catch((error) => {
      console.warn('[Live2D] 初始化失败', error)
    })
  }, [fetchLive2d])

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
        <div className="h-screen w-screen overflow-hidden">
          {/* 全局拖拽区域 - 出现在所有窗口顶部 */}
          <DragRegion />
          {renderContent()}
          <PermissionsGuide />
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
