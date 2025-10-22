import '@/styles/index.css'
import '@/lib/i18n'
import { Outlet } from 'react-router'

import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { ThemeProvider } from '@/components/system/theme/theme-provider'
import { Button } from '@/components/ui/button'
import { Toaster } from '@/components/ui/sonner'
import { useBackendLifecycle } from '@/hooks/useBackendLifecycle'

function App() {
  const { isTauriApp, status, errorMessage, retry } = useBackendLifecycle()

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
          {renderContent()}
          <Toaster position="top-right" />
        </div>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export { App }
