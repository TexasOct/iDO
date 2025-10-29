export function DragRegion() {
  return (
    <div
      data-tauri-drag-region
      className="fixed top-0 right-0 left-0 z-50 h-5 w-full select-none"
      style={
        {
          WebkitAppRegion: 'drag',
          WebkitUserSelect: 'none'
        } as React.CSSProperties
      }
    />
  )
}
