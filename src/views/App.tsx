import '@/styles/index.css'
import '@/lib/i18n'
import { ThemeProvider } from '@/components/system/theme/theme-provider'
import { Outlet } from 'react-router'
import { Toaster } from '@/components/ui/sonner'
import { ErrorBoundary } from '@/components/shared/ErrorBoundary'

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <div className="h-screen w-screen overflow-hidden">
          <Outlet />
          <Toaster position="top-right" />
        </div>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export { App }
