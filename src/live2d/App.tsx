import { useCallback, useState } from 'react'

import * as PIXI from 'pixi.js'
import { emitTo } from '@tauri-apps/api/event'
import { getCurrentWebviewWindow } from '@tauri-apps/api/webviewWindow'
import { writeText } from '@tauri-apps/plugin-clipboard-manager'

import { updateLive2DSettings } from '@/lib/client/apiClient'

import { Live2DStatusOverlay } from './components/Live2DStatusOverlay'
import { Live2DToolbar } from './components/Live2DToolbar'
import { useLive2DDialog } from './hooks/useLive2DDialog'
import { useLive2DModelManager } from './hooks/useLive2DModelManager'
import { useDynamicDragRegion } from './hooks/useDragRegion'

declare global {
  interface Window {
    PIXI: typeof PIXI
  }
}

window.PIXI = PIXI

export default function Live2DApp() {
  const [isResizable, setIsResizable] = useState(false)
  const [isDraggable, setIsDraggable] = useState(false)

  // Use unified drag region hook for canvas - window drag is enabled when NOT in drag or resize mode
  const canvasRef = useDynamicDragRegion<HTMLCanvasElement>(!isDraggable && !isResizable)

  const {
    modelRef,
    currentModelUrlRef,
    winSize,
    status,
    errorMessage,
    availableModels,
    notificationDuration,
    loadModel,
    setStatus,
    setErrorMessage
  } = useLive2DModelManager(canvasRef)

  const { showDialog, dialogText, setDialog, hideDialog, handleChat } = useLive2DDialog(notificationDuration)

  const handleToggleDrag = useCallback(() => {
    const newState = !isDraggable
    setIsDraggable(newState)

    if (modelRef.current) {
      modelRef.current.interactive = newState
      if (newState) {
        let dragData: any = null
        const onDragStart = (event: any) => {
          dragData = event.data
        }
        const onDragMove = () => {
          if (dragData && modelRef.current) {
            const newPosition = dragData.getLocalPosition(modelRef.current.parent)
            modelRef.current.x = newPosition.x
            modelRef.current.y = newPosition.y
          }
        }
        const onDragEnd = () => {
          dragData = null
        }
        modelRef.current.on('pointerdown', onDragStart)
        modelRef.current.on('pointermove', onDragMove)
        modelRef.current.on('pointerup', onDragEnd)
        modelRef.current.on('pointerupoutside', onDragEnd)
      } else {
        modelRef.current.removeAllListeners('pointerdown')
        modelRef.current.removeAllListeners('pointermove')
        modelRef.current.removeAllListeners('pointerup')
        modelRef.current.removeAllListeners('pointerupoutside')
      }
    }

    setDialog(newState ? 'Drag mode enabled' : 'Drag mode disabled')
  }, [isDraggable, modelRef, setDialog])

  const handleToggleResize = useCallback(async () => {
    try {
      const win = getCurrentWebviewWindow()
      const newState = !isResizable
      await win.setResizable(newState)
      setIsResizable(newState)

      setDialog(newState ? 'Resize mode enabled - drag window edges to resize' : 'Resize mode disabled')
    } catch (error) {
      console.error('[Live2D] 切换调整大小模式失败', error)
      setDialog('切换失败: ' + (error instanceof Error ? error.message : String(error)))
    }
  }, [isResizable, setDialog])

  const handleLockWindow = useCallback(async () => {
    try {
      const win = getCurrentWebviewWindow()
      const ok = confirm('Enable cursor event passthrough?')
      if (ok) {
        await win.setIgnoreCursorEvents(true)
        setDialog('Cursor event passthrough enabled')
      }
    } catch (error) {
      console.warn('[Live2D] Failed to set cursor passthrough', error)
    }
  }, [setDialog])

  const handleNextModel = useCallback(async () => {
    if (availableModels.length === 0) return
    const currentUrl = currentModelUrlRef.current
    const currentIndex = availableModels.findIndex((item) => item.url === currentUrl)
    const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % availableModels.length : 0
    const nextModel = availableModels[nextIndex]
    if (!nextModel) return

    setStatus('loading')
    try {
      await loadModel(nextModel.url)
      await updateLive2DSettings({
        selectedModelUrl: nextModel.url
      })
      await emitTo('main', 'live2d-model-updated', { modelUrl: nextModel.url })
      setStatus('ready')
    } catch (error) {
      console.error('[Live2D] 切换模型失败', error)
      setStatus('error')
      setErrorMessage('切换模型失败')
    }
  }, [availableModels, currentModelUrlRef, loadModel, setErrorMessage, setStatus])

  const handleCopyModelUrl = useCallback(async () => {
    if (!currentModelUrlRef.current) return
    try {
      await writeText(currentModelUrlRef.current)
      await emitTo('main', 'live2d-toast', { message: '模型地址已复制' })
    } catch (error) {
      console.warn('[Live2D] 无法复制模型地址', error)
    }
  }, [currentModelUrlRef])

  const handleHideWindow = useCallback(async () => {
    try {
      const win = getCurrentWebviewWindow()
      await win.close()
    } catch (error) {
      console.warn('[Live2D] 关闭窗口失败', error)
    }
  }, [])

  return (
    <div
      className={`live2d-view ${isResizable ? 'edit' : ''}`}
      style={{ width: winSize.width, height: winSize.height }}>
      <div className={`waifu ${isResizable ? 'edit-mode' : ''}`}>
        <canvas ref={canvasRef} id="live2d" className="live2d" />

        {showDialog && (
          <div
            className="waifu-tips show"
            style={{ opacity: showDialog ? 1 : 0, top: '20px', right: '20px' }}
            onClick={hideDialog}>
            {dialogText}
          </div>
        )}

        <Live2DToolbar
          isResizable={isResizable}
          isDraggable={isDraggable}
          onNextModel={handleNextModel}
          onChat={handleChat}
          onToggleDrag={handleToggleDrag}
          onToggleResize={handleToggleResize}
          onCopyModelUrl={handleCopyModelUrl}
          onLockWindow={handleLockWindow}
          onHideWindow={handleHideWindow}
        />

        <Live2DStatusOverlay status={status} errorMessage={errorMessage} />
      </div>
    </div>
  )
}
