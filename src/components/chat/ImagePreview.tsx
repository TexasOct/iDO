/**
 * Image preview component
 * Used to preview images before sending in the message input box
 */

import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ImagePreviewProps {
  images: string[]
  onRemove: (index: number) => void
  readOnly?: boolean
}

export function ImagePreview({ images, onRemove, readOnly = false }: ImagePreviewProps) {
  if (images.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {images.map((image, index) => (
        <div key={index} className="group relative">
          <img src={image} alt={`Preview ${index + 1}`} className="h-20 w-20 rounded-lg border object-cover" />
          {!readOnly && (
            <Button
              size="icon"
              variant="destructive"
              className="absolute -top-2 -right-2 h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100"
              onClick={() => onRemove(index)}>
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      ))}
    </div>
  )
}
