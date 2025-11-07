import { useEffect, useRef, useState } from 'react'

export interface DragRegionOptions {
  enabled?: boolean
  className?: string
  height?: number
  zIndex?: number
}

export interface DragRegionProps {
  'data-tauri-drag-region'?: boolean
  className?: string
  style: React.CSSProperties
}

/**
 * Unified hook for creating draggable window regions in Tauri applications
 *
 * @param options - Configuration options for the drag region
 * @returns Props to spread onto the drag region element
 *
 * @example
 * ```tsx
 * const dragProps = useDragRegion({ enabled: true, height: 40 })
 * return <div {...dragProps}>Draggable Area</div>
 * ```
 */
export function useDragRegion(options: DragRegionOptions = {}): DragRegionProps {
  const { enabled = true, className = '', height = 40, zIndex = 100 } = options

  const [isTauriReady, setIsTauriReady] = useState(typeof window !== 'undefined' && '__TAURI__' in window)

  useEffect(() => {
    if (isTauriReady) return

    let tries = 0
    const checkInterval = setInterval(() => {
      tries += 1
      if (typeof window !== 'undefined' && '__TAURI__' in window) {
        setIsTauriReady(true)
        clearInterval(checkInterval)
      } else if (tries > 20) {
        clearInterval(checkInterval)
      }
    }, 50)

    return () => clearInterval(checkInterval)
  }, [isTauriReady])

  const baseStyle = {
    WebkitAppRegion: enabled ? 'drag' : 'no-drag',
    WebkitUserSelect: 'none',
    userSelect: 'none',
    height: `${height}px`,
    zIndex
  } as React.CSSProperties

  const props: DragRegionProps = {
    className: `select-none ${className}`.trim(),
    style: baseStyle
  }

  // Only add data-tauri-drag-region if Tauri is ready and enabled
  if (isTauriReady && enabled) {
    props['data-tauri-drag-region'] = true
  }

  return props
}

/**
 * Hook for dynamically controlling drag region on an element (like canvas)
 *
 * @param enabled - Whether dragging should be enabled
 * @returns Ref to attach to the element
 *
 * @example
 * ```tsx
 * const canvasRef = useDynamicDragRegion(isDraggable)
 * return <canvas ref={canvasRef} />
 * ```
 */
export function useDynamicDragRegion<T extends HTMLElement>(enabled: boolean): React.RefObject<T | null> {
  const elementRef = useRef<T | null>(null)

  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    if (enabled) {
      element.setAttribute('data-tauri-drag-region', 'true')
      ;(element.style as any).webkitAppRegion = 'drag'
    } else {
      element.removeAttribute('data-tauri-drag-region')
      ;(element.style as any).webkitAppRegion = 'no-drag'
    }
  }, [enabled])

  return elementRef
}

/**
 * Create props for making child elements non-draggable within a drag region
 *
 * @returns Props to spread onto non-draggable elements (like buttons)
 */
export function useNoDragProps(): { style: React.CSSProperties; className: string } {
  return {
    style: { WebkitAppRegion: 'no-drag' } as React.CSSProperties,
    className: 'no-drag pointer-events-auto'
  }
}
