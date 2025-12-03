import { useEffect } from 'react'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { isTauri } from '@/lib/utils/tauri'

/**
 * Hook to handle window close events gracefully on macOS
 *
 * On macOS, closing a fullscreen window directly causes a black desktop issue.
 * This hook:
 * 1. Intercepts the close request
 * 2. Exits fullscreen if needed
 * 3. Hides the window instead of closing it
 */
export function useWindowCloseHandler() {
  useEffect(() => {
    if (!isTauri()) {
      return
    }

    const setupCloseHandler = async () => {
      const window = getCurrentWindow()

      // Listen for close requested event
      const unlisten = await window.onCloseRequested(async (event) => {
        // Prevent default close behavior
        event.preventDefault()

        console.log('[useWindowCloseHandler] Close requested, handling...')

        try {
          // Check if window is fullscreen
          const isFullscreen = await window.isFullscreen()
          console.log('[useWindowCloseHandler] Is fullscreen:', isFullscreen)

          if (isFullscreen) {
            console.log('[useWindowCloseHandler] Exiting fullscreen...')
            // Exit fullscreen first to prevent black screen issue on macOS
            await window.setFullscreen(false)
            console.log('[useWindowCloseHandler] Fullscreen exit initiated')

            // Wait for fullscreen exit animation to complete (macOS needs longer time)
            // Increase to 800ms to ensure animation completes
            await new Promise((resolve) => setTimeout(resolve, 800))
            console.log('[useWindowCloseHandler] Fullscreen exit animation should be complete')
          }

          // Hide the window instead of closing it
          console.log('[useWindowCloseHandler] Attempting to hide window...')
          await window.hide()
          console.log('[useWindowCloseHandler] ✅ Window hidden successfully')
        } catch (error) {
          console.error('[useWindowCloseHandler] ❌ Error handling window close:', error)

          // Fallback: try to hide anyway with additional delay
          try {
            console.log('[useWindowCloseHandler] Trying fallback hide with delay...')
            await new Promise((resolve) => setTimeout(resolve, 200))
            await window.hide()
            console.log('[useWindowCloseHandler] ✅ Fallback hide succeeded')
          } catch (hideError) {
            console.error('[useWindowCloseHandler] ❌ Fallback hide also failed:', hideError)
          }
        }
      })

      return unlisten
    }

    let unlisten: (() => void) | undefined

    setupCloseHandler()
      .then((fn) => {
        unlisten = fn
      })
      .catch((error) => {
        console.error('[useWindowCloseHandler] Failed to setup close handler:', error)
      })

    return () => {
      if (unlisten) {
        unlisten()
      }
    }
  }, [])
}
