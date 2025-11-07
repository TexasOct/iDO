import { useCallback, useEffect, useRef, useState } from 'react'

import { listen } from '@tauri-apps/api/event'

type FriendlyChatPayload = {
  id: string
  message: string
  timestamp: string
}

type QueuedMessage = {
  text: string
  duration?: number
}

const MAX_SEEN_MESSAGE_IDS = 50
const TRANSITION_DELAY = 300 // CSS transition duration in ms

export const useLive2DDialog = (notificationDuration: number) => {
  const [showDialog, setShowDialog] = useState(false)
  const [dialogText, setDialogText] = useState('')
  const dialogTimeoutRef = useRef<number | undefined>(undefined)
  const transitionTimeoutRef = useRef<number | undefined>(undefined)
  const durationRef = useRef(notificationDuration)
  const seenMessageIdsRef = useRef<string[]>([])
  const messageQueueRef = useRef<QueuedMessage[]>([])
  const isProcessingRef = useRef(false)

  useEffect(() => {
    durationRef.current = notificationDuration
  }, [notificationDuration])

  const clearAllTimeouts = useCallback(() => {
    if (dialogTimeoutRef.current) {
      window.clearTimeout(dialogTimeoutRef.current)
      dialogTimeoutRef.current = undefined
    }
    if (transitionTimeoutRef.current) {
      window.clearTimeout(transitionTimeoutRef.current)
      transitionTimeoutRef.current = undefined
    }
  }, [])

  const processNextMessage = useCallback(() => {
    if (isProcessingRef.current || messageQueueRef.current.length === 0) {
      return
    }

    isProcessingRef.current = true
    const message = messageQueueRef.current.shift()!
    const actualDuration = message.duration ?? durationRef.current

    const showMessage = () => {
      setDialogText(message.text)
      setShowDialog(true)

      // 设置消息自动隐藏的定时器
      dialogTimeoutRef.current = window.setTimeout(() => {
        setShowDialog(false)
        dialogTimeoutRef.current = undefined

        // 消息隐藏后，等待过渡动画完成，然后处理下一条消息
        transitionTimeoutRef.current = window.setTimeout(() => {
          isProcessingRef.current = false
          transitionTimeoutRef.current = undefined

          if (messageQueueRef.current.length > 0) {
            processNextMessage()
          }
        }, TRANSITION_DELAY)
      }, actualDuration)
    }

    // 如果当前有对话框显示，先隐藏它
    if (showDialog) {
      setShowDialog(false)

      // 等待隐藏动画完成后再显示新消息
      transitionTimeoutRef.current = window.setTimeout(() => {
        showMessage()
      }, TRANSITION_DELAY)
    } else {
      // 直接显示新消息
      showMessage()
    }
  }, [showDialog])

  const setDialog = useCallback(
    (text: string, duration?: number) => {
      // 清空当前队列，只保留最新的消息（避免消息堆积）
      messageQueueRef.current = [{ text, duration }]

      // 如果当前正在处理消息，中断它并重新开始
      if (isProcessingRef.current) {
        clearAllTimeouts()
        isProcessingRef.current = false
        setShowDialog(false)

        // 等待当前消息完全隐藏后再显示新消息
        transitionTimeoutRef.current = window.setTimeout(() => {
          processNextMessage()
        }, TRANSITION_DELAY)
      } else {
        // 如果没有正在处理的消息，立即开始处理
        processNextMessage()
      }
    },
    [clearAllTimeouts, processNextMessage]
  )

  const hideDialog = useCallback(() => {
    clearAllTimeouts()
    messageQueueRef.current = []
    setShowDialog(false)
    isProcessingRef.current = false
  }, [clearAllTimeouts])

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
    setDialog(randomMessage)
  }, [setDialog])

  useEffect(() => {
    let mounted = true
    const unlistenPromise = listen<FriendlyChatPayload>('friendly-chat-live2d', (event) => {
      if (!mounted) return
      const { message, id } = event.payload

      if (id) {
        const seenIds = seenMessageIdsRef.current
        if (seenIds.includes(id)) {
          return
        }
        seenIds.push(id)
        if (seenIds.length > MAX_SEEN_MESSAGE_IDS) {
          seenIds.shift()
        }
      }

      setDialog(message)
    })

    return () => {
      mounted = false
      clearAllTimeouts()
      unlistenPromise.then((unlisten) => unlisten()).catch(() => {})
    }
  }, [clearAllTimeouts, setDialog])

  return {
    showDialog,
    dialogText,
    setDialog,
    hideDialog,
    handleChat
  }
}
