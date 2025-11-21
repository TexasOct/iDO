/**
 * 消息输入组件
 */

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send, Image as ImageIcon } from 'lucide-react'
import { ImagePreview } from './ImagePreview'
import { useTranslation } from 'react-i18next'
import { useChatStore } from '@/lib/stores/chat'

interface MessageInputProps {
  onSend: (message: string, images?: string[]) => void
  disabled?: boolean
  placeholder?: string
  initialMessage?: string | null
}

export function MessageInput({ onSend, disabled, placeholder, initialMessage }: MessageInputProps) {
  const { t } = useTranslation()
  const [message, setMessage] = useState('')
  const [images, setImages] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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
      setImages(pendingImages || [])
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

  return (
    <div onDrop={handleDrop} onDragOver={handleDragOver} className="bg-background rounded-xl border shadow-sm">
      {/* 图片预览 */}
      {images.length > 0 && (
        <div className="border-b px-3 py-2">
          <ImagePreview images={images} onRemove={removeImage} />
        </div>
      )}

      {/* 输入区域 */}
      <div className="relative flex items-end gap-2 px-3 py-2">
        {/* 左侧按钮组 */}
        <div className="flex shrink-0 items-center gap-1 pb-1">
          <Button
            size="icon"
            variant="ghost"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="h-8 w-8"
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

        {/* 文本输入框 */}
        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={placeholder || 'Reply...'}
          disabled={disabled}
          className="flex-1 resize-none overflow-y-auto rounded-2xl border-0 bg-transparent px-3 py-2.5 shadow-none focus-visible:ring-0"
          style={{ minHeight: '40px', maxHeight: '160px', height: '40px', lineHeight: '1.5' }}
          rows={1}
        />

        {/* 右侧发送按钮 */}
        <div className="shrink-0 pb-1">
          <Button
            onClick={handleSend}
            disabled={disabled || (!message.trim() && images.length === 0)}
            size="icon"
            className="h-8 w-8 rounded-lg">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
