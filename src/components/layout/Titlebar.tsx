/**
 * Transparent drag region overlay for Windows
 * - Only responds to drag events
 * - All other events pass through (pointer-events-none)
 * - Does not occupy render space
 */
export function Titlebar() {
  return (
    <div
      data-tauri-drag-region
      className="pointer-events-auto fixed top-0 right-0 left-0 z-[100] h-10 select-none"
      style={
        {
          WebkitAppRegion: 'drag',
          WebkitUserSelect: 'none'
        } as React.CSSProperties
      }
    />
  )
}
