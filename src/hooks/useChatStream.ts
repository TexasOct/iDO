/**
 * Streaming message hook
 * Listens for streaming message chunks via Tauri events
 */

import { useEffect } from 'react'
import { listen } from '@tauri-apps/api/event'
import type { ChatMessageChunk } from '@/lib/types/chat'
import { useChatStore } from '@/lib/stores/chat'

export function useChatStream(conversationId: string | null) {
  const appendStreamingChunk = useChatStore((state) => state.appendStreamingChunk)
  const setStreamingComplete = useChatStore((state) => state.setStreamingComplete)
  const resetStreaming = useChatStore((state) => state.resetStreaming)

  useEffect(() => {
    if (!conversationId) return

    let unlisten: (() => void) | null = null

    // Listen for streaming message events
    const setupListener = async () => {
      unlisten = await listen<ChatMessageChunk>('chat-message-chunk', (event) => {
        const { conversationId: id, chunk, done, messageId } = event.payload

        if (done) {
          // Handle stream completion for any conversation
          setStreamingComplete(id, messageId)
        } else {
          // Append streamed message chunks for any conversation
          appendStreamingChunk(id, chunk)
        }
      })
    }

    setupListener()

    return () => {
      if (unlisten) {
        unlisten()
      }
      // Note: do not clear streaming state here
      // Switching conversations unmounts this hook while streaming may still be active
      // Let setStreamingComplete clear state when the stream finishes or errors
    }
  }, [conversationId, appendStreamingChunk, setStreamingComplete, resetStreaming])
}
