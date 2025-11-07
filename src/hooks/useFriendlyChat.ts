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
}

const LIVE2D_WINDOW_LABEL = 'rewind-live2d'

/**
 * Hook to listen for friendly chat events and handle notifications
 */
export function useFriendlyChat() {
  // Use refs to track processed message IDs to prevent duplicates
  const processedMessages = useRef<Set<string>>(new Set())
  const isInitialized = useRef(false)

  // Stable callback that doesn't change on every render
  const handleMessage = useCallback((payload: FriendlyChatEventPayload, type: 'notification' | 'live2d') => {
    // Check if already processed
    if (processedMessages.current.has(payload.id)) {
      console.log(`[FriendlyChat] Skipping duplicate message: ${payload.id}`)
      return
    }

    console.log(`[FriendlyChat] ${type} event received:`, payload)

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

    // Get latest settings from store directly
    const currentSettings = useFriendlyChatStore.getState().settings

    // Add message to store
    useFriendlyChatStore.getState().addMessage(message)

    // Handle notification
    if (type === 'notification' && currentSettings.enableSystemNotification) {
      try {
        sendNotification({
          title: 'Rewind AI 朋友',
          body: payload.message,
          icon: 'icons/icon.png'
        })
      } catch (error) {
        console.error('[FriendlyChat] Failed to send system notification:', error)
      }
    }

    // Handle Live2D forwarding
    if (type === 'live2d' && currentSettings.enableLive2dDisplay && isTauri()) {
      emitTo(LIVE2D_WINDOW_LABEL, 'friendly-chat-live2d', payload).catch((error) => {
        console.warn('[FriendlyChat] Failed to forward Live2D event:', error)
      })
      console.log('[FriendlyChat] Forwarded Live2D message to Live2D window')
    }
  }, [])

  useEffect(() => {
    // Prevent multiple initializations
    if (isInitialized.current) {
      console.log('[FriendlyChat] Already initialized, skipping')
      return
    }

    let unlistenNotification: (() => void) | undefined
    let unlistenLive2d: (() => void) | undefined
    let mounted = true

    const setupListeners = async () => {
      if (!mounted) return

      // Listen for system notification events
      const unlisten1 = await listen<FriendlyChatEventPayload>('friendly-chat-notification', (event) => {
        if (mounted) {
          handleMessage(event.payload, 'notification')
        }
      })

      if (!mounted) {
        unlisten1()
        return
      }
      unlistenNotification = unlisten1

      // Listen for Live2D display events
      const unlisten2 = await listen<FriendlyChatEventPayload>('friendly-chat-live2d', (event) => {
        if (mounted) {
          handleMessage(event.payload, 'live2d')
        }
      })

      if (!mounted) {
        unlisten2()
        return
      }
      unlistenLive2d = unlisten2

      isInitialized.current = true
      console.log('[FriendlyChat] Event listeners set up')
    }

    setupListeners().catch((error) => {
      console.error('[FriendlyChat] Failed to setup listeners:', error)
    })

    return () => {
      mounted = false
      // Cleanup listeners
      if (unlistenNotification) {
        unlistenNotification()
      }
      if (unlistenLive2d) {
        unlistenLive2d()
      }
      console.log('[FriendlyChat] Event listeners cleaned up')
    }
  }, [handleMessage]) // Only depend on stable handleMessage callback
}
