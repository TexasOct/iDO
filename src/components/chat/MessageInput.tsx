/**
 * 消息输入组件
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

  // 获取模型列表
  const { models, activeModel } = useModelsStore()
  const [localModelId, setLocalModelId] = useState<string | null>(null)

  // 初始化模型选择
  useEffect(() => {
    if (selectedModelId) {
      setLocalModelId(selectedModelId)
    } else if (activeModel) {
      setLocalModelId(activeModel.id)
    }
  }, [selectedModelId, activeModel])

  // 处理模型变更
  const handleModelChange = (modelId: string) => {
    setLocalModelId(modelId)
    onModelChange?.(modelId)
  }

  // 获取待发送的消息和图片
  const pendingMessage = useChatStore((state) => state.pendingMessage)
  const pendingImages = useChatStore((state) => state.pendingImages)
  const setPendingMessage = useChatStore((state) => state.setPendingMessage)
  const setPendingImages = useChatStore((state) => state.setPendingImages)

  // 自动调整高度
  const adjustHeight = () => {
    const textarea = textareaRef.current
    if (!textarea) return

    // 重置高度以获取正确的 scrollHeight
    textarea.style.height = 'auto'

    // 设置新高度，但不超过最大高度
    const newHeight = Math.min(textarea.scrollHeight, 160) // 最大高度 160px (10rem)
    textarea.style.height = `${newHeight}px`
  }

  // 处理初始消息和图片
  useEffect(() => {
    if (pendingMessage || (pendingImages && pendingImages.length > 0)) {
      setMessage(pendingMessage || '')

      // 如果是文件路径，需要转换为数据 URL 以供预览
      if (pendingImages && pendingImages.length > 0) {
        const convertPaths = async () => {
          const convertedImages: string[] = await Promise.all(
            pendingImages.map(async (img): Promise<string> => {
              // 检查是否已经是数据 URL
              if (img.startsWith('data:')) {
                return img
              }

              // 检查是否是文件路径（包含 / 或 \，且不是 URL）
              if ((img.includes('/') || img.includes('\\')) && !img.startsWith('http')) {
                try {
                  const result = await apiClient.readImageFile({ filePath: img })
                  if (result.success && result.data_url) {
                    return result.data_url as string
                  }
                  // 如果转换失败，保留原始路径
                  return img
                } catch (error) {
                  console.error('Failed to convert image file:', img, error)
                  return img
                }
              }
              // 已经是 base64 或其他格式
              return img
            })
          )
          setImages(convertedImages)
        }
        convertPaths()
      }

      // 清除待发送消息和图片，避免重复设置
      setPendingMessage(null)
      setPendingImages([])
      // 让textarea获取焦点
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
      // 重置高度
      setTimeout(() => adjustHeight(), 0)
    }
  }

  // 监听消息变化，自动调整高度
  useEffect(() => {
    adjustHeight()
  }, [message])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter 发送消息
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
    // Enter 换行（默认行为）
    // 不需要额外处理，让浏览器默认行为处理
  }

  // 处理粘贴事件
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

  // 处理拖拽
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

  // 处理文件选择
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    for (const file of files) {
      if (file.type.startsWith('image/')) {
        await addImageFile(file)
      }
    }
    // 清空 input，允许重复选择同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // 添加图片文件
  const addImageFile = async (file: File) => {
    // 限制图片大小为 5MB
    if (file.size > 5 * 1024 * 1024) {
      alert('图片大小不能超过 5MB')
      return
    }

    // 转换为 base64
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

  // 获取当前选中的模型名称
  const currentModel = models.find((m) => m.id === localModelId)
  const modelDisplayName = currentModel?.name || activeModel?.name || 'Select Model'

  return (
    <div onDrop={handleDrop} onDragOver={handleDragOver} className="bg-background w-full">
      {/* 图片预览 */}
      {images.length > 0 && (
        <div className="mb-2 rounded-lg border p-2">
          <ImagePreview images={images} onRemove={removeImage} />
        </div>
      )}

      {/* 输入区域 */}
      <div className="bg-muted/30 space-y-3 rounded-3xl border px-4 py-3">
        {/* 文本输入框 */}
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

        {/* 底部按钮区域 */}
        <div className="flex items-center justify-between gap-2">
          {/* 左侧：附件按钮 */}
          <div className="flex items-center gap-2">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="h-8 w-8 shrink-0 rounded-full"
              title={t('chat.addImage') || '添加图片'}>
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

          {/* 右侧：模型选择器 + 发送按钮 */}
          <div className="flex shrink-0 items-center gap-2">
            {/* 模型选择器 */}
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

            {/* 发送/停止按钮 */}
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
