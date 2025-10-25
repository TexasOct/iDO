import { useState, useEffect } from 'react'
import { convertFileSrc } from '@tauri-apps/api/core'
import { ImageIcon, Loader2, AlertCircle } from 'lucide-react'

interface ScreenshotThumbnailProps {
  screenshotPath: string
  width?: number
  height?: number
  className?: string
}

/**
 * 截屏缩略图组件
 * 用于在 Activity 时间线中显示截屏事件的预览图
 */
export function ScreenshotThumbnail({
  screenshotPath,
  width = 320,
  height = 180,
  className = ''
}: ScreenshotThumbnailProps) {
  const [imageSrc, setImageSrc] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    // 将本地文件路径转换为 Tauri 安全的 asset URL
    try {
      console.log('[ScreenshotThumbnail] Original path:', screenshotPath)
      console.log('[ScreenshotThumbnail] typeof convertFileSrc:', typeof convertFileSrc)

      const assetUrl = convertFileSrc(screenshotPath, 'asset')

      console.log('[ScreenshotThumbnail] Converted URL:', assetUrl)
      console.log('[ScreenshotThumbnail] URL type:', typeof assetUrl)

      setImageSrc(assetUrl)
      setLoading(false)
    } catch (err) {
      console.error('[ScreenshotThumbnail] Failed to convert file path:', err)
      setError(true)
      setLoading(false)
    }
  }, [screenshotPath])

  const handleImageError = () => {
    console.error('[ScreenshotThumbnail] Failed to load image:', screenshotPath)
    setError(true)
    setLoading(false)
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
