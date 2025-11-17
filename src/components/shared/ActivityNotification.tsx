import { useEffect, useState } from 'react'
import { Bell, X } from 'lucide-react'

interface ActivityNotificationProps {
  count: number
  onDismiss: () => void
  onView: () => void
}

export function ActivityNotification({ count, onDismiss, onView }: ActivityNotificationProps) {
  const [isVisible, setIsVisible] = useState(true)
  const [isAnimating, setIsAnimating] = useState(false)

  useEffect(() => {
    // 显示动画
    const showTimer = setTimeout(() => {
      setIsAnimating(true)
    }, 100)

    // 自动隐藏
    const hideTimer = setTimeout(() => {
      handleDismiss()
    }, 5000)

    return () => {
      clearTimeout(showTimer)
      clearTimeout(hideTimer)
    }
  }, [])

  const handleDismiss = () => {
    setIsAnimating(false)
    setTimeout(() => {
      setIsVisible(false)
      onDismiss()
    }, 300)
  }

  const handleView = () => {
    onView()
    handleDismiss()
  }

  if (!isVisible) return null

  return (
    <div
      className={`bg-primary text-primary-foreground fixed top-4 right-4 z-50 transform rounded-lg px-4 py-3 shadow-lg transition-all duration-300 ${
        isAnimating ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      }`}>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4" />
          <div className="bg-primary-foreground h-2 w-2 animate-pulse rounded-full"></div>
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium">有新活动</p>
          <p className="text-xs opacity-90">{count} 个新活动已添加</p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleView}
            className="bg-primary-foreground/20 hover:bg-primary-foreground/30 rounded px-2 py-1 text-xs transition-colors">
            查看
          </button>
          <button
            onClick={handleDismiss}
            className="text-primary-foreground/70 hover:text-primary-foreground p-1 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
