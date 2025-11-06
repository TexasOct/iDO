import { useState, useEffect, useRef, useCallback } from 'react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { X } from 'lucide-react'

interface PhotoGridProps {
  images: string[]
  title?: string
}

interface ImageDimensions {
  width: number
  height: number
  aspectRatio: number
}

interface RowItem {
  index: number
  aspectRatio: number
}

/**
 * Google Photos-style justified layout component
 * Uses aspect ratio aware layout to minimize gaps and efficiently use space
 * Handles mixed portrait and landscape images well
 */
export function PhotoGrid({ images, title }: PhotoGridProps) {
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null)
  const [dimensions, setDimensions] = useState<ImageDimensions[]>([])
  const [rows, setRows] = useState<RowItem[][]>([])
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(0)

  if (images.length === 0) return null

  const toDataUrl = (value: string) => (value.startsWith('data:') ? value : `data:image/jpeg;base64,${value}`)

  // Load image dimensions
  useEffect(() => {
    const loadDimensions = async () => {
      const dims: ImageDimensions[] = []

      for (const img of images) {
        const imgElement = new Image()
        imgElement.src = toDataUrl(img)

        await new Promise((resolve) => {
          imgElement.onload = () => {
            dims.push({
              width: imgElement.naturalWidth,
              height: imgElement.naturalHeight,
              aspectRatio: imgElement.naturalWidth / imgElement.naturalHeight
            })
            resolve(null)
          }
          imgElement.onerror = () => {
            // Default aspect ratio for failed images
            dims.push({
              width: 1,
              height: 1,
              aspectRatio: 1
            })
            resolve(null)
          }
        })
      }

      setDimensions(dims)
    }

    loadDimensions()
  }, [images])

  // Calculate rows based on aspect ratios
  useEffect(() => {
    if (dimensions.length === 0) return

    const rows: RowItem[][] = []
    let currentRow: RowItem[] = []
    let currentRowAspectRatioSum = 0
    const targetRowWidth = 5 // Ideal sum of aspect ratios per row

    for (let i = 0; i < dimensions.length; i++) {
      const aspectRatio = dimensions[i].aspectRatio
      currentRow.push({ index: i, aspectRatio })
      currentRowAspectRatioSum += aspectRatio

      // Start new row if:
      // 1. Sum of aspect ratios exceeds target (but allow at least 1 image per row)
      // 2. This is the last image
      if (currentRowAspectRatioSum >= targetRowWidth || i === dimensions.length - 1) {
        rows.push([...currentRow])
        currentRow = []
        currentRowAspectRatioSum = 0
      }
    }

    setRows(rows)
  }, [dimensions])

  // Measure container width
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth)
      }
    }

    updateWidth()
    const resizeObserver = new ResizeObserver(updateWidth)
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current)
    }

    return () => resizeObserver.disconnect()
  }, [])

  const calculateRowHeight = useCallback((row: RowItem[], width: number): number => {
    if (width <= 0 || row.length === 0) return 200

    const gap = 4 // gap-1 = 4px in Tailwind
    const totalGap = (row.length - 1) * gap
    const availableWidth = width - totalGap

    // Sum of aspect ratios determines the row height
    const aspectRatioSum = row.reduce((sum, item) => sum + item.aspectRatio, 0)
    const rowHeight = availableWidth / aspectRatioSum

    // Constrain height for reasonable display
    return Math.min(Math.max(rowHeight, 120), 400)
  }, [])

  const handleImageClick = (index: number) => {
    setSelectedImageIndex(index)
  }

  const handleClose = () => {
    setSelectedImageIndex(null)
  }

  const handleNext = () => {
    if (selectedImageIndex !== null) {
      setSelectedImageIndex((selectedImageIndex + 1) % images.length)
    }
  }

  const handlePrev = () => {
    if (selectedImageIndex !== null) {
      setSelectedImageIndex((selectedImageIndex - 1 + images.length) % images.length)
    }
  }

  const renderLayout = () => {
    if (dimensions.length === 0 || rows.length === 0) {
      return (
        <div className="bg-muted/10 flex min-h-[200px] items-center justify-center rounded-lg">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      )
    }

    return (
      <div className="space-y-1">
        {rows.map((row, rowIdx) => {
          const rowHeight = calculateRowHeight(row, containerWidth)

          return (
            <div key={rowIdx} className="flex gap-1" style={{ height: `${rowHeight}px` }}>
              {row.map((item) => {
                return (
                  <div
                    key={item.index}
                    className="bg-muted/10 group relative cursor-pointer overflow-hidden rounded-lg transition-all hover:shadow-md"
                    style={{
                      flex: `${item.aspectRatio} 0 0`,
                      minWidth: 0
                    }}>
                    <img
                      src={toDataUrl(images[item.index])}
                      alt={`${title || 'photo'} ${item.index + 1}`}
                      className="h-full w-full object-cover transition-opacity group-hover:opacity-90"
                      loading="lazy"
                      onClick={() => handleImageClick(item.index)}
                    />
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>
    )
  }

  const viewerTitle =
    selectedImageIndex !== null ? `${title || 'photo'} ${selectedImageIndex + 1}` : `${title || 'photo'} viewer`

  return (
    <>
      <div ref={containerRef} className="photo-grid w-full">
        {renderLayout()}
      </div>

      {/* Fullscreen image viewer */}
      <Dialog open={selectedImageIndex !== null} onOpenChange={(open) => !open && handleClose()}>
        <DialogContent className="max-h-[90vh] max-w-[90vw] border-0 bg-transparent p-0">
          <>
            <DialogTitle className="sr-only">{viewerTitle}</DialogTitle>
            <div className="relative flex items-center justify-center">
              {/* Close button */}
              <button
                onClick={handleClose}
                className="absolute top-4 right-4 z-10 rounded-full bg-black/50 p-2 text-white transition-colors hover:bg-black/70">
                <X className="h-5 w-5" />
              </button>

              {/* Image */}
              {selectedImageIndex !== null && (
                <div className="relative">
                  <img
                    src={toDataUrl(images[selectedImageIndex])}
                    alt={`${title || 'photo'} ${selectedImageIndex + 1}`}
                    className="max-h-[85vh] max-w-full rounded-lg object-contain"
                  />

                  {/* Navigation buttons */}
                  {images.length > 1 && (
                    <>
                      <button
                        onClick={handlePrev}
                        className="absolute top-1/2 left-4 -translate-y-1/2 rounded-full bg-black/50 p-3 text-white transition-colors hover:bg-black/70">
                        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                      </button>
                      <button
                        onClick={handleNext}
                        className="absolute top-1/2 right-4 -translate-y-1/2 rounded-full bg-black/50 p-3 text-white transition-colors hover:bg-black/70">
                        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </>
                  )}

                  {/* Image counter */}
                  <div className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-black/50 px-3 py-1 text-sm text-white">
                    {selectedImageIndex + 1} / {images.length}
                  </div>
                </div>
              )}
            </div>
          </>
        </DialogContent>
      </Dialog>
    </>
  )
}
