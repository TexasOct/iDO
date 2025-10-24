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
      className={`fixed top-4 right-4 z-50 transform rounded-lg bg-blue-500 px-4 py-3 text-white shadow-lg transition-all duration-300 ${
        isAnimating ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      }`}>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4" />
          <div className="h-2 w-2 animate-pulse rounded-full bg-white"></div>
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium">有新活动</p>
          <p className="text-xs opacity-90">{count} 个新活动已添加</p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleView}
            className="rounded bg-white/20 px-2 py-1 text-xs transition-colors hover:bg-white/30">
            查看
          </button>
          <button onClick={handleDismiss} className="p-1 text-white/70 transition-colors hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
