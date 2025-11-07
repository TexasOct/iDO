import type { FC } from 'react'

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
  onHideWindow
}) => (
  <div className="waifu-tool">
    <span className="fui-checkbox-unchecked" title="更换模型" onClick={onNextModel}></span>
    <span className="fui-chat" onClick={onChat} title="聊天"></span>
    <span className="fui-eye" onClick={onNextModel} title="下一个模型"></span>
    <span
      className="fui-location"
      title="调整模型位置"
      style={{ color: isDraggable ? '#117be6' : '' }}
      onClick={onToggleDrag}></span>
    <span
      className="fui-window"
      onClick={onToggleResize}
      title={isResizable ? '退出调整窗口大小' : '调整窗口大小'}></span>
    <span className="fui-alert-circle" onClick={onCopyModelUrl} title="复制模型地址"></span>
    <span className="fui-lock" onClick={onLockWindow} title="忽略鼠标事件"></span>
    <span className="fui-cross" onClick={onHideWindow} title="关闭"></span>
  </div>
)
