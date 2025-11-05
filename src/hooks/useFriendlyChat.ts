import { useEffect } from 'react'
import { listen } from '@tauri-apps/api/event'
import { sendNotification } from '@tauri-apps/plugin-notification'
import { useFriendlyChatStore } from '@/lib/stores/friendlyChat'
import type { FriendlyChatMessage } from '@/lib/types/friendlyChat'

interface FriendlyChatEventPayload {
  id: string
  message: string
  timestamp: string
}

/**
 * Hook to listen for friendly chat events and handle notifications
 */
export function useFriendlyChat() {
  const { settings, addMessage } = useFriendlyChatStore()

  useEffect(() => {
    let unlistenNotification: (() => void) | undefined
    let unlistenLive2d: (() => void) | undefined

    const setupListeners = async () => {
      // Listen for system notification events
      const unlisten1 = await listen<FriendlyChatEventPayload>('friendly-chat-notification', async (event) => {
        const payload = event.payload
        console.log('[FriendlyChat] Notification event received:', payload)

        // Add to message history
        const message: FriendlyChatMessage = {
          id: payload.id,
          message: payload.message,
          timestamp: payload.timestamp,
          createdAt: payload.timestamp
        }
        addMessage(message)

        // Show system notification if enabled
        if (settings.enableSystemNotification) {
          try {
            await sendNotification({
              title: 'Rewind AI 朋友',
              body: payload.message,
              icon: 'icons/icon.png'
            })
            console.log('[FriendlyChat] System notification sent')
          } catch (error) {
            console.error('[FriendlyChat] Failed to send system notification:', error)
          }
        }
      })
      unlistenNotification = unlisten1

      // Listen for Live2D display events
      const unlisten2 = await listen<FriendlyChatEventPayload>('friendly-chat-live2d', (event) => {
        const payload = event.payload
        console.log('[FriendlyChat] Live2D event received:', payload)

        // Add to message history
        const message: FriendlyChatMessage = {
          id: payload.id,
          message: payload.message,
          timestamp: payload.timestamp,
          createdAt: payload.timestamp
        }
        addMessage(message)

        // The Live2D window will handle displaying the message
        // We just need to emit the event to it
        if (settings.enableLive2dDisplay) {
          // The event is already emitted by backend, Live2D window should listen to it
          console.log('[FriendlyChat] Live2D display enabled, message will show in Live2D window')
        }
      })
      unlistenLive2d = unlisten2

      console.log('[FriendlyChat] Event listeners set up')
    }

    setupListeners().catch((error) => {
      console.error('[FriendlyChat] Failed to setup listeners:', error)
    })

    return () => {
      // Cleanup listeners
      if (unlistenNotification) {
        unlistenNotification()
      }
      if (unlistenLive2d) {
        unlistenLive2d()
      }
      console.log('[FriendlyChat] Event listeners cleaned up')
    }
  }, [settings.enableSystemNotification, settings.enableLive2dDisplay, addMessage])
}
