import { useCallback, useEffect, useRef, useState } from 'react'

import { listen } from '@tauri-apps/api/event'

type FriendlyChatPayload = {
  id: string
  message: string
  timestamp: string
  notificationDuration?: number
  notification_duration?: number
  duration?: number
  durationMs?: number
  duration_ms?: number
}

const normalizePayloadDuration = (payload: FriendlyChatPayload): number | undefined => {
  const candidates = [
    payload.notificationDuration,
    payload.notification_duration,
    payload.duration,
    payload.durationMs,
    payload.duration_ms
  ]

  for (const value of candidates) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value
    }
  }

  return undefined
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
    console.log('[Live2DDialog] Default notification duration changed to:', notificationDuration, 'ms')
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

    console.log('[Live2DDialog] Processing message with duration:', actualDuration, 'ms')

    const showMessage = () => {
      setDialogText(message.text)
      setShowDialog(true)

      // 设置消息自动隐藏的定时器
      dialogTimeoutRef.current = window.setTimeout(() => {
        console.log('[Live2DDialog] Auto-hiding message after', actualDuration, 'ms')
        setShowDialog(false)
        dialogTimeoutRef.current = undefined

        // 消息隐藏后，等待过渡动画完成，然后处理下一条消息
        transitionTimeoutRef.current = window.setTimeout(() => {
          isProcessingRef.current = false
          transitionTimeoutRef.current = undefined

          if (messageQueueRef.current.length > 0) {
            console.log('[Live2DDialog] Processing next message in queue')
            processNextMessage()
          }
        }, TRANSITION_DELAY)
      }, actualDuration)
    }

    // 使用 ref 检查当前状态，避免闭包问题
    setShowDialog((currentShow) => {
      if (currentShow) {
        // 如果当前有对话框显示，先隐藏它
        transitionTimeoutRef.current = window.setTimeout(() => {
          showMessage()
        }, TRANSITION_DELAY)
        return false
      } else {
        // 直接显示新消息
        showMessage()
        return true
      }
    })
  }, [])

  const setDialog = useCallback(
    (text: string, duration?: number) => {
      console.log('[Live2DDialog] New message queued:', { text: text.substring(0, 30) + '...', duration })

      // 添加到队列（不清空，支持多条消息）
      messageQueueRef.current.push({ text, duration })
      console.log('[Live2DDialog] Queue length:', messageQueueRef.current.length)

      // 如果当前没有正在处理的消息，立即开始处理
      if (!isProcessingRef.current) {
        processNextMessage()
      }
      // 如果正在处理消息，新消息会在当前消息完成后自动处理
    },
    [processNextMessage]
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
          console.log('[Live2DDialog] Duplicate message, ignoring:', id)
          return
        }
        seenIds.push(id)
        if (seenIds.length > MAX_SEEN_MESSAGE_IDS) {
          seenIds.shift()
        }
      }

      const durationOverride = normalizePayloadDuration(event.payload)
      const finalDuration = durationOverride ?? durationRef.current
      console.log('[Live2DDialog] Received message:')
      console.log('  - Override duration:', durationOverride, 'ms')
      console.log('  - Default duration:', durationRef.current, 'ms')
      console.log('  - Final duration:', finalDuration, 'ms')
      console.log('  - Raw payload:', event.payload)
      setDialog(message, durationOverride)
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
