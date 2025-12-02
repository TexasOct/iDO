import type { CSSProperties, FC } from 'react'

type Live2DToolbarProps = {
  isResizable: boolean
  isDraggable: boolean
  onNextModel: () => void
  onChat: () => void
  onToggleDrag: () => void
  onToggleResize: () => void
  onCopyModelUrl: () => void
  onLockWindow: () => void
  onHideWindow: () => void
  onOpenDevTools?: () => void
  toolbarScale?: number
}

type ToolbarStyle = CSSProperties & {
  '--live2d-toolbar-scale'?: number
}

export const Live2DToolbar: FC<Live2DToolbarProps> = ({
  isResizable,
  isDraggable,
  onNextModel,
  onChat,
  onToggleDrag,
  onToggleResize,
  onCopyModelUrl,
  onLockWindow,
  onHideWindow,
  onOpenDevTools,
  toolbarScale = 1
}) => {
  const clampedScale = Math.max(0.55, Math.min(toolbarScale, 1.2))
  const toolbarStyle: ToolbarStyle = {
    '--live2d-toolbar-scale': clampedScale
  }

  return (
    <div className="waifu-tool" style={toolbarStyle}>
      <span className="fui-checkbox-unchecked" title="Switch model" onClick={onNextModel}></span>
      <span className="fui-chat" onClick={onChat} title="Chat"></span>
      <span className="fui-eye" onClick={onNextModel} title="Next model"></span>
      <span
        className="fui-location"
        title="Adjust model position"
        style={{ color: isDraggable ? '#117be6' : '' }}
        onClick={onToggleDrag}></span>
      <span
        className="fui-window"
        onClick={onToggleResize}
        title={isResizable ? 'Exit window resize' : 'Resize window'}></span>
      <span className="fui-alert-circle" onClick={onCopyModelUrl} title="Copy model address"></span>
      {onOpenDevTools && <span className="fui-gear" onClick={onOpenDevTools} title="Developer tools"></span>}
      <span className="fui-lock" onClick={onLockWindow} title="Ignore mouse events"></span>
      <span className="fui-cross" onClick={onHideWindow} title="Close"></span>
    </div>
  )
}
