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

      // Set up an auto-hide timer for the dialog
      dialogTimeoutRef.current = window.setTimeout(() => {
        console.log('[Live2DDialog] Auto-hiding message after', actualDuration, 'ms')
        setShowDialog(false)
        dialogTimeoutRef.current = undefined

        // After the dialog hides, wait for the transition before processing the next message
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

    // Use refs to check state and avoid stale closures
    setShowDialog((currentShow) => {
      if (currentShow) {
        // Hide the current dialog if one is visible
        transitionTimeoutRef.current = window.setTimeout(() => {
          showMessage()
        }, TRANSITION_DELAY)
        return false
      } else {
        // Immediately show the new message
        showMessage()
        return true
      }
    })
  }, [])

  const setDialog = useCallback(
    (text: string, duration?: number) => {
      console.log('[Live2DDialog] New message queued:', { text: text.substring(0, 30) + '...', duration })

      // Add to the queue (no clearing, supports multiple messages)
      messageQueueRef.current.push({ text, duration })
      console.log('[Live2DDialog] Queue length:', messageQueueRef.current.length)

      // If nothing is processing, start immediately
      if (!isProcessingRef.current) {
        processNextMessage()
      }
      // If a message is already processing, handle the new one afterward
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
      'Hello there!',
      'How is your day going?',
      'Need a short break?',
      'Remember to drink water!',
      'Keep it up—you got this!',
      'Do not push yourself too hard!'
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
