/**
 * Hook to sync streaming status from backend
 * Periodically fetches which conversations are currently streaming
 */

import { useEffect, useRef } from 'react'
import * as apiClient from '@/lib/client/apiClient'
import { useChatStore } from '@/lib/stores/chat'

const SYNC_INTERVAL = 3000 // 3 seconds

export function useStreamingStatus(enabled: boolean = true) {
  const conversations = useChatStore((state) => state.conversations)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!enabled) return

    const syncStreamingStatus = async () => {
      try {
        // Get conversation IDs to check
        const conversationIds = conversations.map((c) => c.id)

        if (conversationIds.length === 0) return

        const response = await apiClient.getStreamingStatus({
          conversationIds
        })

        if (response.success && response.data) {
          const data = response.data as {
            activeStreams: string[]
            streamingStatus: Record<string, boolean>
            activeCount: number
          }
          const { streamingStatus } = data

          // Update store with backend streaming status
          useChatStore.setState((state) => {
            let needsUpdate = false
            let newStreamingConversationId = state.streamingConversationId

            // Check if current streaming conversation is still streaming
            if (state.streamingConversationId) {
              const isStillStreaming = streamingStatus[state.streamingConversationId]
              if (!isStillStreaming) {
                // Backend says it's no longer streaming, clear it
                newStreamingConversationId = null
                needsUpdate = true
              }
            }

            // Find any conversation that's streaming according to backend
            // but not marked as streaming in frontend
            for (const [convId, isStreaming] of Object.entries(streamingStatus)) {
              if (isStreaming && state.streamingConversationId !== convId) {
                // Backend says this conversation is streaming, but frontend doesn't know
                newStreamingConversationId = convId
                needsUpdate = true
                break
              }
            }

            if (needsUpdate) {
              return {
                streamingConversationId: newStreamingConversationId
              }
            }

            return state
          })
        }
      } catch (error) {
        console.error('Failed to sync streaming status:', error)
      }
    }

    // Initial sync
    syncStreamingStatus()

    // Set up periodic sync
    intervalRef.current = setInterval(syncStreamingStatus, SYNC_INTERVAL)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [enabled, conversations])
}
