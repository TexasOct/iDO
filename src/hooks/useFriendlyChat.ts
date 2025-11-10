import { useEffect, useRef, useCallback } from 'react'
import { emitTo, listen } from '@tauri-apps/api/event'
import { sendNotification } from '@tauri-apps/plugin-notification'
import { useFriendlyChatStore } from '@/lib/stores/friendlyChat'
import type { FriendlyChatMessage } from '@/lib/types/friendlyChat'
import { isTauri } from '@/lib/utils/tauri'

interface FriendlyChatEventPayload {
  id: string
  message: string
  timestamp: string
  notificationDuration?: number
  notification_duration?: number
  duration?: number
  durationMs?: number
  duration_ms?: number
}

const LIVE2D_WINDOW_LABEL = 'ido-live2d'
const normalizeDuration = (payload: FriendlyChatEventPayload): number | undefined => {
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

/**
 * Hook to listen for friendly chat events and handle notifications
 */
export function useFriendlyChat() {
  // Use refs to track processed message IDs to prevent duplicates
  const processedMessages = useRef<Set<string>>(new Set())
  const isInitialized = useRef(false)

  // Stable callback that doesn't change on every render
  const handleMessage = useCallback((payload: FriendlyChatEventPayload) => {
    // Check if already processed
    if (processedMessages.current.has(payload.id)) {
      console.log(`[FriendlyChat] Duplicate message ${payload.id}, ignoring`)
      return
    }

    // Mark as processed
    processedMessages.current.add(payload.id)

    // Cleanup old processed IDs (keep last 100)
    if (processedMessages.current.size > 100) {
      const array = Array.from(processedMessages.current)
      processedMessages.current = new Set(array.slice(-100))
    }

    // Add to message history
    const message: FriendlyChatMessage = {
      id: payload.id,
      message: payload.message,
      timestamp: payload.timestamp,
      createdAt: payload.timestamp
    }
    useFriendlyChatStore.getState().addMessage(message)

    // Get latest settings from store directly
    const currentSettings = useFriendlyChatStore.getState().settings

    // Handle system notification
    if (currentSettings.enableSystemNotification) {
      try {
        sendNotification({
          title: 'iDO AI 朋友',
          body: payload.message,
          icon: 'icons/icon.png'
        })
        console.log('[FriendlyChat] Sent system notification')
      } catch (error) {
        console.error('[FriendlyChat] Failed to send system notification:', error)
      }
    }

    // Handle Live2D forwarding
    if (currentSettings.enableLive2dDisplay && isTauri()) {
      const durationOverride = normalizeDuration(payload)
      const forwardedPayload =
        typeof durationOverride === 'number' ? { ...payload, notificationDuration: durationOverride } : payload

      console.log('[FriendlyChat] Forwarding to Live2D with duration:', durationOverride, 'ms')

      emitTo(LIVE2D_WINDOW_LABEL, 'friendly-chat-live2d', forwardedPayload).catch((error) => {
        console.warn('[FriendlyChat] Failed to forward Live2D event:', error)
      })
    }
  }, [])

  useEffect(() => {
    // Prevent multiple initializations
    if (isInitialized.current) {
      console.log('[FriendlyChat] Already initialized, skipping')
      return
    }

    let unlistenNotification: (() => void) | undefined
    let mounted = true

    const setupListeners = async () => {
      if (!mounted) return

      // Listen for friendly chat events from backend
      // This is the single source of truth - backend sends only one event
      // and this hook handles both notification and Live2D forwarding
      const unlisten = await listen<FriendlyChatEventPayload>('friendly-chat-notification', (event) => {
        if (mounted) {
          handleMessage(event.payload)
        }
      })

      if (!mounted) {
        unlisten()
        return
      }
      unlistenNotification = unlisten

      isInitialized.current = true
    }

    setupListeners().catch((error) => {
      console.error('[FriendlyChat] Failed to setup listeners:', error)
    })

    return () => {
      mounted = false
      // Cleanup listener
      if (unlistenNotification) {
        unlistenNotification()
      }
    }
  }, [handleMessage]) // Only depend on stable handleMessage callback
}
