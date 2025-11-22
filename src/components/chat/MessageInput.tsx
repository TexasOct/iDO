/**
 * Message input component
 */

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Send, Image as ImageIcon, Square } from 'lucide-react'
import { ImagePreview } from './ImagePreview'
import { useTranslation } from 'react-i18next'
import { useChatStore } from '@/lib/stores/chat'
import { useModelsStore } from '@/lib/stores/models'
import * as apiClient from '@/lib/client/apiClient'

interface MessageInputProps {
  onSend: (message: string, images?: string[]) => void
  onCancel?: () => void
  disabled?: boolean
  isStreaming?: boolean
  isCancelling?: boolean
  placeholder?: string
  initialMessage?: string | null
  conversationId?: string | null
  selectedModelId?: string | null
  onModelChange?: (modelId: string) => void
}

export function MessageInput({
  onSend,
  onCancel,
  disabled,
  isStreaming,
  isCancelling,
  placeholder,
  initialMessage,
  selectedModelId,
  onModelChange
}: MessageInputProps) {
  const { t } = useTranslation()
  const [message, setMessage] = useState('')
  const [images, setImages] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Fetch the model list
  const { models, activeModel } = useModelsStore()
  const [localModelId, setLocalModelId] = useState<string | null>(null)

  // Initialize the selected model
  useEffect(() => {
    if (selectedModelId) {
      setLocalModelId(selectedModelId)
    } else if (activeModel) {
      setLocalModelId(activeModel.id)
    }
  }, [selectedModelId, activeModel])

  // Handle model changes
  const handleModelChange = (modelId: string) => {
    setLocalModelId(modelId)
    onModelChange?.(modelId)
  }

  // Read the pending message and images
  const pendingMessage = useChatStore((state) => state.pendingMessage)
  const pendingImages = useChatStore((state) => state.pendingImages)
  const setPendingMessage = useChatStore((state) => state.setPendingMessage)
  const setPendingImages = useChatStore((state) => state.setPendingImages)

  // Automatically adjust the textarea height
  const adjustHeight = () => {
    const textarea = textareaRef.current
    if (!textarea) return

    // Reset height to measure the correct scrollHeight
    textarea.style.height = 'auto'

    // Apply the new height without exceeding the maximum
    const newHeight = Math.min(textarea.scrollHeight, 160) // Max height 160px (10rem)
    textarea.style.height = `${newHeight}px`
  }

  // Handle initial message and images
  useEffect(() => {
    if (pendingMessage || (pendingImages && pendingImages.length > 0)) {
      setMessage(pendingMessage || '')

      // Convert file paths to data URLs for preview
      if (pendingImages && pendingImages.length > 0) {
        const convertPaths = async () => {
          const convertedImages: string[] = await Promise.all(
            pendingImages.map(async (img): Promise<string> => {
              // Check if the value is already a data URL
              if (img.startsWith('data:')) {
                return img
              }

              // Detect file paths (contain / or \ and are not URLs)
              if ((img.includes('/') || img.includes('\\')) && !img.startsWith('http')) {
                try {
                  const result = await apiClient.readImageFile({ filePath: img })
                  if (result.success && result.data_url) {
                    return result.data_url as string
                  }
                  // If conversion fails, keep the original path
                  return img
                } catch (error) {
                  console.error('Failed to convert image file:', img, error)
                  return img
                }
              }
              // Already base64 or another supported format
              return img
            })
          )
          setImages(convertedImages)
        }
        convertPaths()
      }

      // Clear pending message and images to avoid duplicates
      setPendingMessage(null)
      setPendingImages([])
      // Focus the textarea
      setTimeout(() => {
        textareaRef.current?.focus()
      }, 0)
    } else if (initialMessage) {
      setMessage(initialMessage)
      setTimeout(() => {
        textareaRef.current?.focus()
      }, 0)
    }
  }, [pendingMessage, pendingImages, initialMessage, setPendingMessage, setPendingImages])

  const handleSend = () => {
    if ((message.trim() || images.length > 0) && !disabled) {
      onSend(message.trim(), images)
      setMessage('')
      setImages([])
      // Reset the height
      setTimeout(() => adjustHeight(), 0)
    }
  }

  // Watch message changes and auto-adjust height
  useEffect(() => {
    adjustHeight()
  }, [message])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter sends the message
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
    // Enter inserts a newline (default behavior)
    // No customization needed; rely on default browser behavior
  }

  // Handle paste events
  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items
    if (!items) return

    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (file) {
          await addImageFile(file)
        }
      }
    }
  }

  // Handle drag-and-drop
  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files)
    for (const file of files) {
      if (file.type.startsWith('image/')) {
        await addImageFile(file)
      }
    }
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
  }

  // Handle file selection
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    for (const file of files) {
      if (file.type.startsWith('image/')) {
        await addImageFile(file)
      }
    }
    // Clear the input so the same file can be reselected
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Add image files
  const addImageFile = async (file: File) => {
    // Limit image size to 5 MB
    if (file.size > 5 * 1024 * 1024) {
      alert('图片大小不能超过 5MB')
      return
    }

    // Convert to base64
    const reader = new FileReader()
    reader.onload = (e) => {
      const base64 = e.target?.result as string
      setImages((prev) => [...prev, base64])
    }
    reader.readAsDataURL(file)
  }

  const removeImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index))
  }

  // Get the currently selected model name
  const currentModel = models.find((m) => m.id === localModelId)
  const modelDisplayName = currentModel?.name || activeModel?.name || 'Select Model'

  return (
    <div onDrop={handleDrop} onDragOver={handleDragOver} className="bg-background w-full">
      {/* Image preview */}
      {images.length > 0 && (
        <div className="mb-2 rounded-lg border p-2">
          <ImagePreview images={images} onRemove={removeImage} />
        </div>
      )}

      {/* Input area */}
      <div className="bg-muted/30 space-y-3 rounded-3xl border px-4 py-3">
        {/* Text input */}
        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={placeholder || t('chat.inputPlaceholder') || 'Send a message'}
          disabled={disabled}
          className="placeholder:text-muted-foreground/60 w-full resize-none overflow-y-auto border-0 bg-transparent! p-2 shadow-none focus-visible:ring-0"
          style={{ minHeight: '24px', maxHeight: '160px', height: '24px', lineHeight: '1.5' }}
          rows={1}
        />

        {/* Bottom button bar */}
        <div className="flex items-center justify-between gap-2">
          {/* Left: attachment button */}
          <div className="flex items-center gap-2">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="h-8 w-8 shrink-0 rounded-full"
              title={t('chat.addImage') || 'Add image'}>
              <ImageIcon className="h-4 w-4" />
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>

          {/* Right: model selector + send button */}
          <div className="flex shrink-0 items-center gap-2">
            {/* Model selector */}
            <Select value={localModelId || undefined} onValueChange={handleModelChange}>
              <SelectTrigger className="hover:bg-muted bg-muted h-8 w-auto gap-2 rounded-xl border-0 px-3 shadow-none focus:ring-0">
                <SelectValue>
                  <span className="text-xs font-medium">{modelDisplayName}</span>
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {models.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    <div className="flex flex-col">
                      <span className="font-medium">{model.name}</span>
                      <span className="text-muted-foreground text-xs">
                        {model.provider} · {model.model}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Send/stop button */}
            {isStreaming ? (
              <Button
                onClick={onCancel}
                disabled={isCancelling}
                size="icon"
                variant="ghost"
                className="h-8 w-8 rounded-full">
                <Square className="h-3.5 w-3.5" />
              </Button>
            ) : (
              <Button
                onClick={handleSend}
                disabled={disabled || (!message.trim() && images.length === 0)}
                size="icon"
                className="h-8 w-8 rounded-full">
                <Send className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
