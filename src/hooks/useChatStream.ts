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

        if (done) {
          // 流式完成 - 处理任何会话的完成事件
          setStreamingComplete(id, messageId)
        } else {
          // 追加消息块 - 处理任何会话的消息块
          appendStreamingChunk(id, chunk)
        }
      })
    }

    setupListener()

    return () => {
      if (unlisten) {
        unlisten()
      }
      // 注意：不要在这里清理流式状态
      // 因为切换对话时这个 hook 会卸载，但流式消息可能还在进行中
      // 流式状态应该在流式完成或错误时由 setStreamingComplete 清理
    }
  }, [conversationId, appendStreamingChunk, setStreamingComplete, resetStreaming])
}
