import '@/styles/index.css'
import '@/lib/i18n'
import { useEffect } from 'react'
import { Outlet } from 'react-router'

import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import { ThemeProvider } from '@/components/system/theme/theme-provider'
import { Toaster } from '@/components/ui/sonner'
import { startBackend, stopBackend } from '@/lib/services/system'
import { isTauri } from '@/lib/utils/tauri'

function App() {
  useEffect(() => {
    if (!isTauri()) {
      return
    }

    let removeReadyListener: (() => void) | undefined
    let removeCloseListener: (() => void) | undefined
    let backendStopped = false

    const setup = async () => {
      try {
        const [{ listen }, { appWindow }] = await Promise.all([
          import('@tauri-apps/api/event'),
          import('@tauri-apps/api/window')
        ])

        const start = async () => {
          try {
            await startBackend()
          } catch (error) {
            console.error('启动后端系统失败', error)
          }
        }

        const stop = async () => {
          if (backendStopped) {
            return
          }

          backendStopped = true

          try {
            await stopBackend()
          } catch (error) {
            console.error('停止后端系统失败', error)
          }
        }

        // 监听 ready 事件，重复调用保证可靠启动
        removeReadyListener = await listen('tauri://ready', async () => {
          await start()
          if (removeReadyListener) {
            removeReadyListener()
            removeReadyListener = undefined
          }
        })

        // 如果事件已触发，立即尝试启动（若未准备好会在 ready 回调再次尝试）
        await start()

        removeCloseListener = await appWindow.onCloseRequested(async (event) => {
          event.preventDefault()

          if (removeCloseListener) {
            removeCloseListener()
            removeCloseListener = undefined
          }

          await stop()
          await appWindow.close()
        })
      } catch (error) {
        console.error('初始化后端生命周期逻辑失败', error)
      }
    }

    void setup()

    return () => {
      const runCleanup = async () => {
        if (removeReadyListener) {
          removeReadyListener()
        }

        if (removeCloseListener) {
          removeCloseListener()
        }

        if (!backendStopped) {
          backendStopped = true
          try {
            await stopBackend()
          } catch (error) {
            console.error('组件卸载时停止后端失败', error)
          }
        }
      }

      void runCleanup()
    }
  }, [])

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
