import { useCallback, useEffect, useMemo, useState } from 'react'

/**
 * Custom titlebar overlay.
 * - Always provides a drag region.
 * - Renders window controls only on Windows.
 */
export function Titlebar() {
  const isWindows = useMemo(() => {
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
  }, [])

  const [isMaximized, setIsMaximized] = useState(false)

  // Track maximize state (only meaningful in Tauri, safe to no-op in web)
  useEffect(() => {
    if (!isWindows) return
    let unsub: (() => void) | undefined
    const init = async () => {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window')
        const win = getCurrentWindow()
        setIsMaximized(await win.isMaximized())
        unsub = await win.onResized(async () => {
          try {
            setIsMaximized(await win.isMaximized())
          } catch {}
        })
      } catch {
        // not in Tauri or window API unavailable
      }
    }
    void init()
    return () => {
      if (unsub) unsub()
    }
  }, [isWindows])

  const handleMinimize = useCallback(async () => {
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window')
      await getCurrentWindow().minimize()
    } catch {}
  }, [])

  const handleMaximize = useCallback(async () => {
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window')
      const win = getCurrentWindow()
      const max = await win.isMaximized()
      if (max) {
        await win.unmaximize()
        setIsMaximized(false)
      } else {
        await win.maximize()
        setIsMaximized(true)
      }
    } catch {}
  }, [])

  const handleClose = useCallback(async () => {
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window')
      await getCurrentWindow().close()
    } catch {}
  }, [])

  return (
    <div
      data-tauri-drag-region
      className="pointer-events-auto fixed top-0 right-0 left-0 z-100 h-10 select-none"
      style={{ WebkitAppRegion: 'drag', WebkitUserSelect: 'none' } as React.CSSProperties}>
      {isWindows ? (
        <div className="flex h-full items-center justify-end gap-1.5 pr-3">
          <button
            aria-label="Minimize"
            onClick={handleMinimize}
            className="text-foreground/80 hover:bg-foreground/15 grid h-9 w-9 place-items-center rounded-lg"
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
            <svg width="12" height="12" viewBox="0 0 10 10" fill="currentColor">
              <rect x="1.3" y="4.6" width="7.4" height="0.8" rx="0.3" />
            </svg>
          </button>
          <button
            aria-label={isMaximized ? 'Restore' : 'Maximize'}
            onClick={handleMaximize}
            className="text-foreground/80 hover:bg-foreground/15 grid h-9 w-9 place-items-center rounded-lg"
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
            {isMaximized ? (
              <svg width="12" height="12" viewBox="0 0 10 10" fill="currentColor">
                <path d="M3 3h6v6H3V3zm1 1v4h4V4H4z" />
              </svg>
            ) : (
              <svg width="12" height="12" viewBox="0 0 10 10" fill="currentColor">
                <rect x="2" y="2" width="6" height="6" rx="0.5" ry="0.5" />
              </svg>
            )}
          </button>
          <button
            aria-label="Close"
            onClick={handleClose}
            className="grid h-9 w-9 place-items-center rounded-lg text-red-500 hover:bg-red-500/15"
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
            <svg width="12" height="12" viewBox="0 0 10 10" fill="currentColor">
              <path d="M2.3 2.3l5.4 5.4m0-5.4l-5.4 5.4" stroke="currentColor" strokeWidth="1.2" />
            </svg>
          </button>
        </div>
      ) : null}
    </div>
  )
}
