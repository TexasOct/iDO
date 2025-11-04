import { useState, useEffect } from 'react'
import { convertFileSrc } from '@tauri-apps/api/core'
import { ImageIcon, Loader2, AlertCircle } from 'lucide-react'
import { fetchImageBase64ByHash } from '@/lib/services/images'

interface ScreenshotThumbnailProps {
  screenshotPath?: string
  screenshotHash?: string
  base64Data?: string // 直接传入 base64 数据（用于未持久化的截图）
  width?: number
  height?: number
  className?: string
}

/**
 * 截屏缩略图组件
 * 支持三种数据源：
 * 1. base64Data - 内存中的截图（未持久化）
 * 2. screenshotPath - 本地文件路径（已持久化）
 * 3. screenshotHash - 通过 hash 标识（备选方案）
 */
export function ScreenshotThumbnail({
  screenshotPath,
  screenshotHash,
  base64Data,
  width = 320,
  height = 180,
  className = ''
}: ScreenshotThumbnailProps) {
  const [imageSrc, setImageSrc] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [fallbackTried, setFallbackTried] = useState(false)

  useEffect(() => {
    // 优先级：base64Data > screenshotPath > screenshotHash
    const loadImage = async () => {
      try {
        setLoading(true)
        setError(false)
        setFallbackTried(false)

        // 1. 如果有 base64 数据，直接使用（内存中的截图）
        if (base64Data) {
          console.log('[ScreenshotThumbnail] Using base64 data from memory')
          setImageSrc(`data:image/jpeg;base64,${base64Data}`)
          setLoading(false)
          return
        }

        // 2. 如果有文件路径，转换为 asset URL（已持久化的截图）
        if (screenshotPath) {
          console.log('[ScreenshotThumbnail] Loading from path:', screenshotPath)
          const assetUrl = convertFileSrc(screenshotPath, 'asset')
          console.log('[ScreenshotThumbnail] Converted URL:', assetUrl)
          setImageSrc(assetUrl)
          setLoading(false)
          return
        }

        // 3. 如果只有 hash，尝试从缓存加载
        if (screenshotHash) {
          console.log('[ScreenshotThumbnail] Only hash provided, fetching from cache:', screenshotHash)
          const base64 = await fetchImageBase64ByHash(screenshotHash)
          if (base64) {
            console.log('[ScreenshotThumbnail] Successfully loaded from cache')
            setImageSrc(`data:image/jpeg;base64,${base64}`)
            setError(false)
            setLoading(false)
          } else {
            console.warn('[ScreenshotThumbnail] Hash provided but image not in cache:', screenshotHash)
            setError(true)
            setLoading(false)
          }
          return
        }

        // 没有任何数据源
        console.error('[ScreenshotThumbnail] No image source provided')
        setError(true)
        setLoading(false)
      } catch (err) {
        console.error('[ScreenshotThumbnail] Failed to load image:', err)
        setError(true)
        setLoading(false)
      }
    }

    void loadImage()
  }, [base64Data, screenshotHash, screenshotPath])

  const handleImageError = () => {
    if (!screenshotHash || fallbackTried) {
      setError(true)
      setLoading(false)
      return
    }

    setFallbackTried(true)
    setLoading(true)

    void (async () => {
      const base64 = await fetchImageBase64ByHash(screenshotHash)
      if (base64) {
        console.log('[ScreenshotThumbnail] Fallback to cached base64 for hash:', screenshotHash)
        setImageSrc(`data:image/jpeg;base64,${base64}`)
        setError(false)
        setLoading(false)
      } else {
        console.warn('[ScreenshotThumbnail] Fallback base64 unavailable for hash:', screenshotHash)
        setError(true)
        setLoading(false)
      }
    })()
  }

  const handleImageLoad = () => {
    setLoading(false)
    setError(false)
  }

  if (loading) {
    return (
      <div
        className={`bg-muted flex items-center justify-center rounded-md ${className}`}
        style={{ width: `${width}px`, height: `${height}px` }}>
        <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div
        className={`bg-muted flex flex-col items-center justify-center gap-2 rounded-md ${className}`}
        style={{ width: `${width}px`, height: `${height}px` }}>
        <AlertCircle className="text-muted-foreground h-6 w-6" />
        <span className="text-muted-foreground text-xs">Failed to load image</span>
      </div>
    )
  }

  return (
    <div
      className={`group relative overflow-hidden rounded-md ${className}`}
      style={{ width: `${width}px`, height: `${height}px` }}>
      <img
        src={imageSrc}
        alt="Screenshot"
        className="h-full w-full object-contain transition-transform duration-200 group-hover:scale-105"
        onError={handleImageError}
        onLoad={handleImageLoad}
        loading="lazy"
      />
      {/* 悬浮时显示图标提示 */}
      <div className="absolute top-2 left-2 rounded bg-black/50 p-1 opacity-0 transition-opacity group-hover:opacity-100">
        <ImageIcon className="h-3 w-3 text-white" />
      </div>
    </div>
  )
}
