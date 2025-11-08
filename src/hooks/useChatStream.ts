/**
 * 流式消息 Hook
 * 监听 Tauri Events 的流式消息块
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

    // 监听流式消息事件
    const setupListener = async () => {
      unlisten = await listen<ChatMessageChunk>('chat-message-chunk', (event) => {
        const { conversationId: id, chunk, done, messageId } = event.payload

        // 只处理当前对话的消息
        if (id !== conversationId) return

        if (done) {
          // 流式完成
          setStreamingComplete(conversationId, messageId)
        } else {
          // 追加消息块
          appendStreamingChunk(chunk)
        }
      })
    }

    setupListener()

    return () => {
      if (unlisten) {
        unlisten()
      }
      // 清理流式状态
      resetStreaming()
    }
  }, [conversationId, appendStreamingChunk, setStreamingComplete, resetStreaming])
}
