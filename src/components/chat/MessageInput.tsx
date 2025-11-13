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

  // 获取待发送的消息
  const pendingMessage = useChatStore((state) => state.pendingMessage)
  const setPendingMessage = useChatStore((state) => state.setPendingMessage)

  // 处理初始消息
  useEffect(() => {
    if (pendingMessage) {
      setMessage(pendingMessage)
      // 清除待发送消息，避免重复设置
      setPendingMessage(null)
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
  }, [pendingMessage, initialMessage, setPendingMessage])

  const handleSend = () => {
    if ((message.trim() || images.length > 0) && !disabled) {
      onSend(message.trim(), images)
      setMessage('')
      setImages([])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter 发送消息
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
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
    <div className="border-t" onDrop={handleDrop} onDragOver={handleDragOver}>
      {/* 图片预览 */}
      {images.length > 0 && (
        <div className="border-b px-4 pt-2">
          <ImagePreview images={images} onRemove={removeImage} />
        </div>
      )}

      {/* 输入区域 */}
      <div className="flex gap-2 p-4">
        <div className="flex flex-col gap-2">
          <Button
            size="icon"
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
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

        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={placeholder || '输入消息... (Cmd/Ctrl + Enter 发送，支持粘贴/拖拽图片)'}
          disabled={disabled}
          className="resize-none"
          rows={3}
        />

        <Button
          onClick={handleSend}
          disabled={disabled || (!message.trim() && images.length === 0)}
          size="icon"
          className="self-end">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
