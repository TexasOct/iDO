import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction
} from 'react'

import * as PIXI from 'pixi.js'
import { InternalModel, Live2DModel } from 'pixi-live2d-display'
import { listen } from '@tauri-apps/api/event'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { getCurrentWebviewWindow } from '@tauri-apps/api/webviewWindow'

import { getLive2DSettings } from '@/lib/client/apiClient'

type LoadModelPayload = {
  modelUrl?: string
  url?: string
}

type Live2DModelItem = {
  url: string
  name?: string
}

type LogicalSize = {
  width: number
  height: number
}

type Live2DModelManagerResult = {
  appRef: MutableRefObject<PIXI.Application | null>
  modelRef: MutableRefObject<Live2DModel<InternalModel> | null>
  currentModelUrlRef: MutableRefObject<string | null>
  winSize: LogicalSize
  status: 'loading' | 'ready' | 'error'
  errorMessage: string | null
  availableModels: Live2DModelItem[]
  notificationDuration: number
  loadModel: (modelUrl: string) => Promise<void>
  setStatus: Dispatch<SetStateAction<'loading' | 'ready' | 'error'>>
  setErrorMessage: Dispatch<SetStateAction<string | null>>
}

export const useLive2DModelManager = (
  canvasRef: MutableRefObject<HTMLCanvasElement | null>
): Live2DModelManagerResult => {
  const appRef = useRef<PIXI.Application | null>(null)
  const modelRef = useRef<Live2DModel<InternalModel> | null>(null)
  const currentModelUrlRef = useRef<string | null>(null)
  const [winSize, setWinSize] = useState<LogicalSize>({ width: 500, height: 400 })
  const winSizeRef = useRef(winSize)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [availableModels, setAvailableModels] = useState<Live2DModelItem[]>([])
  const [notificationDuration, setNotificationDuration] = useState(5000)

  const updateWinSize = useCallback((size: LogicalSize) => {
    winSizeRef.current = size
    setWinSize(size)
  }, [])

  const toLogicalSize = useCallback((size: LogicalSize) => {
    const dpr = window.devicePixelRatio || 1
    return {
      width: size.width / dpr,
      height: size.height / dpr
    }
  }, [])

  const disposeModel = useCallback(() => {
    if (modelRef.current) {
      if (appRef.current && modelRef.current.parent) {
        appRef.current.stage.removeChild(modelRef.current)
      }
      modelRef.current.destroy({ children: true, texture: true, baseTexture: true })
      modelRef.current = null
    }
  }, [])

  const ensureApp = useCallback(async () => {
    if (appRef.current) {
      return appRef.current
    }

    if (!canvasRef.current) {
      throw new Error('Canvas container not available')
    }

    const app = new PIXI.Application({
      view: canvasRef.current as HTMLCanvasElement,
      resizeTo: window,
      backgroundAlpha: 0
    } as any)

    app.stage.sortableChildren = true
    appRef.current = app
    return app
  }, [canvasRef])

  const fitModelToStage = useCallback(
    (model: Live2DModel<InternalModel>, app: PIXI.Application, logicalView?: LogicalSize) => {
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

      const scaleX = viewWidth / baseWidth
      const scaleY = viewHeight / baseHeight
      const scale = Math.min(scaleX, scaleY)

      model.scale.set(scale)
      model.x = viewWidth / 2
      model.y = viewHeight / 2
    },
    []
  )

  const loadModel = useCallback(
    async (modelUrl: string) => {
      if (!modelUrl) {
        throw new Error('模型地址为空')
      }

      const app = await ensureApp()

      setStatus('loading')
      setErrorMessage(null)

      try {
        disposeModel()

        const model = await Live2DModel.from(modelUrl, {
          autoUpdate: true
        })

        model.anchor.set(0.5, 0.5)
        modelRef.current = model
        model.zIndex = 1
        model.interactive = false
        model.buttonMode = false

        if (app.stage.children.length > 0) {
          app.stage.removeChildren()
        }

        app.stage.addChild(model)
        currentModelUrlRef.current = modelUrl

        fitModelToStage(model, app, winSizeRef.current)

        model.once('ready', () => {
          if (appRef.current && modelRef.current) {
            fitModelToStage(modelRef.current, appRef.current, winSizeRef.current)
          }
        })

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
        const win = getCurrentWebviewWindow()
        const size = await win.innerSize()
        const logicalSize = toLogicalSize({ width: size.width, height: size.height })
        updateWinSize(logicalSize)

        const result = await getLive2DSettings(undefined)
        const payload = (result?.data as any) || {}
        const settings = payload.settings || {}
        const modelUrl = settings.selectedModelUrl || settings.selected_model_url
        const duration = settings.notificationDuration || settings.notification_duration || 5000
        const localModels = Array.isArray(payload.models?.local) ? payload.models.local : []
        const remoteModels = Array.isArray(payload.models?.remote) ? payload.models.remote : []
        const models = [...localModels, ...remoteModels].filter(
          (item: any) => typeof item?.url === 'string'
        ) as Live2DModelItem[]

        setNotificationDuration(duration)
        setAvailableModels(models)

        if (modelUrl) {
          await loadModel(modelUrl)
        } else if (models.length > 0) {
          await loadModel(models[0].url)
        } else {
          setStatus('error')
          setErrorMessage('No default model configured')
        }
      } catch (error) {
        if (!mounted) return
        console.error('[Live2D] 初始化失败', error)
        setStatus('error')
        setErrorMessage(error instanceof Error ? error.message : String(error))
      }
    }

    bootstrap()

    const tearDown = () => {
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
  }, [canvasRef, disposeModel, fitModelToStage, loadModel, toLogicalSize, updateWinSize])

  useEffect(() => {
    let disposed = false
    let unlistenResize: (() => void) | null = null
    let resizeTimeout: number | undefined

    const setup = async () => {
      try {
        const currentWindow = getCurrentWindow()

        const cleanupResize = await currentWindow.onResized(() => {
          if (disposed) return

          if (resizeTimeout) {
            window.clearTimeout(resizeTimeout)
          }

          resizeTimeout = window.setTimeout(async () => {
            const size = await currentWindow.innerSize()
            const logicalSize = toLogicalSize({ width: size.width, height: size.height })

            updateWinSize(logicalSize)

            if (appRef.current && modelRef.current) {
              appRef.current.renderer.resize(logicalSize.width, logicalSize.height)

              await new Promise((resolve) => requestAnimationFrame(resolve))

              fitModelToStage(modelRef.current, appRef.current, logicalSize)
            }
          }, 100)
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

  return {
    appRef,
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
  }
}
