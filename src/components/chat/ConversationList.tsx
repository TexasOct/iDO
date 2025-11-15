/**
 * 对话列表组件
 */

import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { Conversation } from '@/lib/types/chat'
import { MessageSquare, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { useTranslation } from 'react-i18next'

interface ConversationListProps {
  conversations: Conversation[]
  currentConversationId: string | null
  onSelect: (conversationId: string) => void
  onNew: () => void
  onDelete: (conversationId: string) => void
}

export function ConversationList({
  conversations,
  currentConversationId,
  onSelect,
  onNew,
  onDelete
}: ConversationListProps) {
  const { t } = useTranslation()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null)

  const handleDeleteClick = (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setConversationToDelete(conversationId)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = () => {
    if (conversationToDelete) {
      onDelete(conversationToDelete)
      setDeleteDialogOpen(false)
      setConversationToDelete(null)
    }
  }

  const formatDate = (conversation: Conversation) => {
    // 使用 updatedAt 作为显示时间（最后更新时间）
    const updatedAt = new Date(conversation.updatedAt)
    const now = new Date()

    // 判断是否是今天
    const isSameDay =
      updatedAt.getFullYear() === now.getFullYear() &&
      updatedAt.getMonth() === now.getMonth() &&
      updatedAt.getDate() === now.getDate()

    if (isSameDay) {
      // 今天的对话：只显示时间（24小时制）
      return new Intl.DateTimeFormat(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).format(updatedAt)
    }

    // 非今天的对话：显示日期
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).format(updatedAt)
  }

  return (
    <div className="flex h-full max-w-xs min-w-[200px] flex-col border-r">
      {/* 头部 */}
      <div className="border-b p-4">
        <Button onClick={onNew} className="w-full" size="sm">
          <Plus className="mr-2 h-4 w-4" />
          {t('chat.newConversation')}
        </Button>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="text-muted-foreground flex h-full flex-col items-center justify-center px-4">
            <MessageSquare className="mb-2 h-12 w-12 opacity-50" />
            <p className="text-center text-sm">{t('chat.noConversations')}</p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={cn(
                  'group hover:bg-accent relative flex cursor-pointer items-center gap-2 rounded-lg p-3 transition-colors',
                  currentConversationId === conversation.id && 'bg-accent'
                )}
                onClick={() => onSelect(conversation.id)}>
                <MessageSquare className="text-muted-foreground h-4 w-4 shrink-0" />
                <div className="flex min-w-0 flex-1 flex-col">
                  <div className="flex items-center">
                    <p className="flex-1 truncate text-sm font-medium">{conversation.title}</p>
                    <span className="text-muted-foreground ml-2 shrink-0 text-right text-xs">
                      {formatDate(conversation)}
                    </span>
                  </div>
                </div>
                {/* 删除按钮 */}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
                  onClick={(e) => handleDeleteClick(conversation.id, e)}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('chat.deleteConversation')}</DialogTitle>
            <DialogDescription>
              {t('chat.confirmDelete')} {t('chat.deleteWarning')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
