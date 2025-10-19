export function DragRegion() {
  return (
    <div
      data-tauri-drag-region
      className="fixed left-0 right-0 top-0 z-50 h-5 w-full select-none"
      style={{
        WebkitAppRegion: 'drag',
        WebkitUserSelect: 'none',
      } as React.CSSProperties}
    />
  )
}
