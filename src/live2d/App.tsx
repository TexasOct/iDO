import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import * as PIXI from 'pixi.js'
import { InternalModel, Live2DModel } from 'pixi-live2d-display'
import { emitTo, listen } from '@tauri-apps/api/event'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { getCurrentWebviewWindow } from '@tauri-apps/api/webviewWindow'
import { writeText } from '@tauri-apps/plugin-clipboard-manager'

import { getLive2dSettings, updateLive2dSettings } from '@/lib/client/apiClient'

import './style.css'

declare global {
  interface Window {
    PIXI: typeof PIXI
  }
}

window.PIXI = PIXI

type LoadModelPayload = {
  modelUrl?: string
  url?: string
}

export default function Live2DApp() {
  const wrapperRef = useRef<HTMLDivElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const appRef = useRef<PIXI.Application | null>(null)
  const modelRef = useRef<Live2DModel<InternalModel> | null>(null)
  const currentModelUrlRef = useRef<string | null>(null)
  const [winSize, setWinSize] = useState({ width: 500, height: 400 })
  const winSizeRef = useRef(winSize)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [availableModels, setAvailableModels] = useState<{ url: string; name?: string }[]>([])
  const [isResizable, setIsResizable] = useState(false)
  const [isDraggable, setIsDraggable] = useState(false)
  const [showDialog, setShowDialog] = useState(false)
  const [dialogText, setDialogText] = useState('')
  const dialogTimeoutRef = useRef<number | undefined>(undefined)

  const updateWinSize = useCallback((size: { width: number; height: number }) => {
    winSizeRef.current = size
    setWinSize(size)
  }, [])
  const toLogicalSize = useCallback((size: { width: number; height: number }) => {
    const dpr = window.devicePixelRatio || 1
    return {
      width: size.width / dpr,
      height: size.height / dpr
    }
  }, [])

  const disposeModel = useCallback(() => {
    if (modelRef.current) {
      console.log('[Live2D] Disposing current model')
      // Remove from stage first
      if (appRef.current && modelRef.current.parent) {
        appRef.current.stage.removeChild(modelRef.current)
      }
      // Then destroy
      modelRef.current.destroy({ children: true, texture: true, baseTexture: true })
      modelRef.current = null
      console.log('[Live2D] Model disposed')
    }
  }, [])

  const ensureApp = useCallback(async () => {
    if (appRef.current) {
      return appRef.current
    }

    if (!canvasRef.current) {
      throw new Error('Canvas container not available')
    }

    console.log('[Live2D] Creating PIXI Application')

    const app = new PIXI.Application({
      view: canvasRef.current as HTMLCanvasElement,
      resizeTo: window,
      backgroundAlpha: 0
    } as any)

    console.log('[Live2D] PIXI Application created, view size:', {
      width: app.view.width,
      height: app.view.height,
      screenWidth: app.screen.width,
      screenHeight: app.screen.height
    })

    app.stage.sortableChildren = true
    appRef.current = app
    return app
  }, [])

  const fitModelToStage = useCallback(
    (model: Live2DModel<InternalModel>, app: PIXI.Application, logicalView?: { width: number; height: number }) => {
      model.anchor.set(0.5, 0.5)

      const baseWidth = model.internalModel?.width ?? model.width / (model.scale.x || 1)
      const baseHeight = model.internalModel?.height ?? model.height / (model.scale.y || 1)

      if (!baseWidth || !baseHeight) {
        console.warn('[Live2D] Cannot fit model - no dimensions available')
        return
      }

      const viewCanvas = app.renderer.view as HTMLCanvasElement | undefined
      const resolution = app.renderer.resolution || window.devicePixelRatio || 1

      const safeNumber = (value?: number | null) => {
        if (!value || value <= 0 || Number.isNaN(value)) return undefined
        return value
      }

      const calculatedWidth =
        typeof viewCanvas?.width === 'number' ? viewCanvas.width / resolution : app.renderer.width / resolution
      const calculatedHeight =
        typeof viewCanvas?.height === 'number' ? viewCanvas.height / resolution : app.renderer.height / resolution

      const viewWidth =
        safeNumber(logicalView?.width) ??
        safeNumber(viewCanvas?.clientWidth) ??
        safeNumber(calculatedWidth) ??
        winSizeRef.current.width
      const viewHeight =
        safeNumber(logicalView?.height) ??
        safeNumber(viewCanvas?.clientHeight) ??
        safeNumber(calculatedHeight) ??
        winSizeRef.current.height

      if (!viewWidth || !viewHeight) {
        console.warn('[Live2D] Cannot fit model - no view dimensions available')
        return
      }

      console.log('[Live2D] Fitting model:', {
        baseModelSize: { width: baseWidth, height: baseHeight },
        viewSize: { width: viewWidth, height: viewHeight },
        currentScale: { x: model.scale.x, y: model.scale.y },
        resolution
      })

      const scaleX = viewWidth / baseWidth
      const scaleY = viewHeight / baseHeight
      const scale = Math.min(scaleX, scaleY)

      console.log('[Live2D] Calculated scale:', { scaleX, scaleY, finalScale: scale })
      model.scale.set(scale)
      model.x = viewWidth / 2
      model.y = viewHeight / 2

      console.log('[Live2D] Model positioned at:', {
        x: model.x,
        y: model.y,
        scale: model.scale.x,
        anchor: { x: model.anchor.x, y: model.anchor.y },
        viewSize: { width: viewWidth, height: viewHeight }
      })
    },
    []
  )

  const loadModel = useCallback(
    async (modelUrl: string) => {
      console.log('[Live2D] loadModel called with URL:', modelUrl)
      if (!modelUrl) {
        throw new Error('模型地址为空')
      }

      const app = await ensureApp()
      console.log('[Live2D] PIXI app initialized:', app)
      console.log('[Live2D] Stage children before load:', app.stage.children.length)

      setStatus('loading')
      setErrorMessage(null)

      try {
        disposeModel()
        console.log('[Live2D] Stage children after dispose:', app.stage.children.length)

        console.log('[Live2D] Loading model from:', modelUrl)
        const model = await Live2DModel.from(modelUrl, {
          autoUpdate: true
        })
        console.log('[Live2D] Model loaded:', model)

        // Set anchor to center before adding to stage
        model.anchor.set(0.5, 0.5)

        modelRef.current = model
        model.zIndex = 1
        model.interactive = false
        model.buttonMode = false

        // Ensure stage is clean before adding
        if (app.stage.children.length > 0) {
          console.warn('[Live2D] Stage not empty! Cleaning up...')
          app.stage.removeChildren()
        }

        app.stage.addChild(model)
        currentModelUrlRef.current = modelUrl
        console.log('[Live2D] Stage children after add:', app.stage.children.length)

        // Fit model immediately after adding to stage
        console.log('[Live2D] Calling fitModelToStage immediately')
        fitModelToStage(model, app, winSizeRef.current)

        // Also listen to ready event for re-fitting
        model.once('ready', () => {
          console.log('[Live2D] Model ready event fired, refitting')
          if (appRef.current && modelRef.current) {
            fitModelToStage(modelRef.current, appRef.current, winSizeRef.current)
          }
        })

        console.log('[Live2D] Model added to stage, setting status to ready')
        setStatus('ready')
      } catch (error) {
        console.error('[Live2D] 模型加载失败', error)
        setStatus('error')
        setErrorMessage(error instanceof Error ? error.message : String(error))
        currentModelUrlRef.current = null
        disposeModel()
      }
    },
    [disposeModel, ensureApp, fitModelToStage]
  )

  useEffect(() => {
    let mounted = true

    const bootstrap = async () => {
      try {
        console.log('[Live2D] Bootstrap started')
        // Get window size
        const win = getCurrentWebviewWindow()
        const size = await win.innerSize()
        console.log('[Live2D] Window size:', size)
        const logicalSize = toLogicalSize({ width: size.width, height: size.height })
        console.log('[Live2D] Logical window size:', logicalSize)
        updateWinSize(logicalSize)

        console.log('[Live2D] Fetching settings...')
        const result = await getLive2dSettings(undefined)
        console.log('[Live2D] Settings result:', result)
        const payload = (result?.data as any) || {}
        const settings = payload.settings || {}
        const modelUrl = settings.selectedModelUrl || settings.selected_model_url
        const localModels = Array.isArray(payload.models?.local) ? payload.models.local : []
        const remoteModels = Array.isArray(payload.models?.remote) ? payload.models.remote : []
        const models = [...localModels, ...remoteModels].filter((item: any) => typeof item?.url === 'string')

        console.log('[Live2D] Models found:', models)
        console.log('[Live2D] Selected model URL:', modelUrl)

        setAvailableModels(
          models.map((item: any) => ({
            url: item.url,
            name: item.name
          }))
        )

        if (modelUrl) {
          console.log('[Live2D] Loading selected model:', modelUrl)
          await loadModel(modelUrl)
        } else if (models.length > 0) {
          // Load first available model if no default is set
          console.log('[Live2D] Loading first available model:', models[0].url)
          await loadModel(models[0].url)
        } else {
          console.error('[Live2D] No models found!')
          setStatus('error')
          setErrorMessage('未找到默认模型配置')
        }

        // Enable window dragging
        if (canvasRef.current) {
          canvasRef.current.setAttribute('data-tauri-drag-region', 'true')
          console.log('[Live2D] Window dragging enabled')
        }
      } catch (error) {
        if (!mounted) return
        console.error('[Live2D] 初始化失败', error)
        setStatus('error')
        setErrorMessage(error instanceof Error ? error.message : String(error))
      }
    }

    bootstrap()

    const tearDown = async () => {
      disposeModel()
      if (appRef.current) {
        appRef.current.destroy(true, { children: true, texture: true, baseTexture: true })
        appRef.current = null
      }
    }

    const handleResize = () => {
      if (!appRef.current || !modelRef.current) return
      fitModelToStage(modelRef.current, appRef.current, {
        width: window.innerWidth,
        height: window.innerHeight
      })
    }

    window.addEventListener('resize', handleResize)
    const unlistenProm = listen<LoadModelPayload>('live2d-load-model', async (event) => {
      const url = event.payload?.modelUrl || event.payload?.url
      if (url && url !== currentModelUrlRef.current) {
        await loadModel(url)
      }
    })

    return () => {
      mounted = false
      window.removeEventListener('resize', handleResize)
      unlistenProm.then((unlisten) => unlisten()).catch(() => {})
      tearDown()
    }
  }, [disposeModel, fitModelToStage, loadModel, toLogicalSize, updateWinSize])

  useEffect(() => {
    let disposed = false
    let unlistenResize: (() => void) | null = null
    let resizeTimeout: number | undefined

    const setup = async () => {
      try {
        const currentWindow = getCurrentWindow()

        // Handle window resize with debounce
        const cleanupResize = await currentWindow.onResized((sizeEvent) => {
          if (disposed) return

          // Clear previous timeout
          if (resizeTimeout) {
            window.clearTimeout(resizeTimeout)
          }

          // Debounce resize handling
          resizeTimeout = window.setTimeout(async () => {
            const size = await currentWindow.innerSize()
            console.log('[Live2D] Window resized to:', size)

            const logicalSize = toLogicalSize({ width: size.width, height: size.height })
            console.log('[Live2D] Logical resize dimensions:', logicalSize)

            // Update window size state
            updateWinSize(logicalSize)

            // Resize PIXI renderer if app exists
            if (appRef.current && modelRef.current) {
              console.log('[Live2D] Resizing renderer and re-fitting model')

              // Resize the renderer (this will also resize the canvas)
              appRef.current.renderer.resize(logicalSize.width, logicalSize.height)

              // Wait for renderer to update
              await new Promise((resolve) => requestAnimationFrame(resolve))

              // Re-fit model to new size
              console.log('[Live2D] Calling fitModelToStage after resize')
              fitModelToStage(modelRef.current, appRef.current, logicalSize)

              console.log('[Live2D] Resize complete')
            }
          }, 100) // 100ms debounce
        })
        if (disposed) {
          cleanupResize()
        } else {
          unlistenResize = cleanupResize
        }
      } catch (error) {
        console.warn('[Live2D] 注册窗口监听失败', error)
      }
    }

    setup()

    return () => {
      disposed = true
      if (resizeTimeout) {
        window.clearTimeout(resizeTimeout)
      }
      unlistenResize?.()
    }
  }, [fitModelToStage, toLogicalSize, updateWinSize])

  const setDialog = useCallback((text: string, duration = 3000) => {
    if (dialogTimeoutRef.current) window.clearTimeout(dialogTimeoutRef.current)
    setDialogText(text)
    setShowDialog(true)
    dialogTimeoutRef.current = window.setTimeout(() => setShowDialog(false), duration)
  }, [])

  const hideDialog = useCallback(() => setShowDialog(false), [])

  const handleChat = useCallback(() => {
    const messages = [
      '你好呀~',
      '今天过得怎么样？',
      '要不要休息一下？',
      '记得多喝水哦~',
      '加油！你可以的！',
      '别太累了~'
    ]
    const randomMessage = messages[Math.floor(Math.random() * messages.length)]
    setDialog(randomMessage, 3000)
  }, [setDialog])

  const handleToggleDrag = useCallback(() => {
    const newState = !isDraggable
    setIsDraggable(newState)
    if (modelRef.current) {
      modelRef.current.interactive = newState
      if (newState) {
        // Enable drag
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

        // Disable window dragging when dragging model
        if (canvasRef.current) {
          canvasRef.current.removeAttribute('data-tauri-drag-region')
          console.log('[Live2D] Window dragging disabled for model drag mode')
        }
      } else {
        // Disable drag
        modelRef.current.removeAllListeners('pointerdown')
        modelRef.current.removeAllListeners('pointermove')
        modelRef.current.removeAllListeners('pointerup')
        modelRef.current.removeAllListeners('pointerupoutside')

        // Re-enable window dragging
        if (canvasRef.current) {
          canvasRef.current.setAttribute('data-tauri-drag-region', 'true')
          console.log('[Live2D] Window dragging enabled')
        }
      }
    }
    setDialog(newState ? '已启用拖拽模式' : '已禁用拖拽模式')
  }, [isDraggable, setDialog])

  const handleToggleResize = useCallback(async () => {
    try {
      const win = getCurrentWebviewWindow()
      const newState = !isResizable
      console.log('[Live2D] Toggling resize mode to:', newState)
      await win.setResizable(newState)
      setIsResizable(newState)

      // Disable window dragging when in resize mode, enable it otherwise
      if (canvasRef.current) {
        if (newState) {
          canvasRef.current.removeAttribute('data-tauri-drag-region')
          console.log('[Live2D] Window dragging disabled for resize mode')
        } else {
          canvasRef.current.setAttribute('data-tauri-drag-region', 'true')
          console.log('[Live2D] Window dragging enabled')
        }
      }

      setDialog(newState ? '已启用调整大小模式 - 拖动窗口边缘调整大小' : '已禁用调整大小模式')
    } catch (error) {
      console.error('[Live2D] 切换调整大小模式失败', error)
      setDialog('切换失败: ' + (error instanceof Error ? error.message : String(error)))
    }
  }, [isResizable, setDialog])

  const handleLockWindow = useCallback(async () => {
    try {
      const win = getCurrentWebviewWindow()
      const ok = confirm('确认开启鼠标事件穿透吗？')
      if (ok) {
        await win.setIgnoreCursorEvents(true)
        setDialog('鼠标事件穿透已开启')
      }
    } catch (error) {
      console.warn('[Live2D] 设置鼠标穿透失败', error)
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
      await updateLive2dSettings({
        selectedModelUrl: nextModel.url
      })
      await emitTo('main', 'live2d-model-updated', { modelUrl: nextModel.url })
      setStatus('ready')
    } catch (error) {
      console.error('[Live2D] 切换模型失败', error)
      setStatus('error')
      setErrorMessage('切换模型失败')
    }
  }, [availableModels, loadModel])

  const handleCopyModelUrl = useCallback(async () => {
    if (!currentModelUrlRef.current) return
    try {
      await writeText(currentModelUrlRef.current)
      await emitTo('main', 'live2d-toast', { message: '模型地址已复制' })
    } catch (error) {
      console.warn('[Live2D] 复制模型地址失败', error)
    }
  }, [])

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
      ref={wrapperRef}
      className={`live2d-view ${isResizable ? 'edit' : ''}`}
      style={{ width: winSize.width, height: winSize.height }}
    >
      <div className={`waifu ${isResizable ? 'edit-mode' : ''}`}>
        <canvas ref={canvasRef} id="live2d" className="live2d" />

        {showDialog && (
          <div
            className="waifu-tips show"
            style={{
              opacity: showDialog ? 1 : 0,
              top: '20px',
              right: '20px'
            }}
            onClick={hideDialog}
          >
            {dialogText}
          </div>
        )}

        <div className="waifu-tool">
          <span className="fui-checkbox-unchecked" title="更换模型" onClick={handleNextModel}></span>
          <span className="fui-chat" onClick={handleChat} title="聊天"></span>
          <span className="fui-eye" onClick={handleNextModel} title="下一个模型"></span>
          <span
            className="fui-location"
            title="调整模型位置"
            style={{ color: isDraggable ? '#117be6' : '' }}
            onClick={handleToggleDrag}
          ></span>
          <span className="fui-window" onClick={handleToggleResize} title="调整窗口大小"></span>
          <span className="fui-alert-circle" onClick={handleCopyModelUrl} title="复制模型地址"></span>
          <span className="fui-lock" onClick={handleLockWindow} title="忽略鼠标事件"></span>
          <span className="fui-cross" onClick={handleHideWindow} title="关闭"></span>
        </div>

        {status === 'loading' && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: 'rgba(32, 33, 36, 0.75)',
              borderRadius: '12px',
              padding: '16px 24px',
              fontSize: '14px',
              color: '#ffffffcc',
              backdropFilter: 'blur(12px)',
              boxShadow: '0 10px 40px rgba(15, 23, 42, 0.45)'
            }}
          >
            模型加载中...
          </div>
        )}
        {status === 'error' && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: 'rgba(209, 67, 67, 0.8)',
              borderRadius: '12px',
              padding: '16px 24px',
              fontSize: '14px',
              color: '#fff',
              backdropFilter: 'blur(12px)',
              boxShadow: '0 10px 40px rgba(15, 23, 42, 0.45)'
            }}
          >
            <div>模型加载失败</div>
            {errorMessage && (
              <div style={{ marginTop: '6px', fontSize: '12px', opacity: 0.9 }}>{errorMessage}</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
