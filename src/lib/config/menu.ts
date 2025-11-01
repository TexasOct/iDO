import { LucideIcon, Clock, History, Sparkles, BarChart, Bot, Settings, MessageSquare } from 'lucide-react'

export interface MenuItem {
  id: string
  labelKey: string // i18n translation key
  icon: LucideIcon
  path: string
  position?: 'main' | 'bottom' // 菜单位置
  badge?: number // 角标数字（可选）
  hidden?: boolean // 是否隐藏
}

export const MENU_ITEMS: MenuItem[] = [
  {
    id: 'activity',
    labelKey: 'menu.activity',
    icon: Clock,
    path: '/activity',
    position: 'main'
  },
  {
    id: 'recent-events',
    labelKey: 'menu.recentEvents',
    icon: History,
    path: '/events',
    position: 'main'
  },
  {
    id: 'ai-summary',
    labelKey: 'menu.aiSummary',
    icon: Sparkles,
    path: '/insights',
    position: 'main'
  },
  {
    id: 'chat',
    labelKey: 'menu.chat',
    icon: MessageSquare,
    path: '/chat',
    position: 'main'
  },
  {
    id: 'agents',
    labelKey: 'menu.agents',
    icon: Bot,
    path: '/agents',
    position: 'main'
  },
  {
    id: 'dashboard',
    labelKey: 'menu.dashboard',
    icon: BarChart,
    path: '/dashboard',
    position: 'main'
  },
  {
    id: 'settings',
    labelKey: 'menu.settings',
    icon: Settings,
    path: '/settings',
    position: 'bottom'
  }
]

// 根据位置分组菜单项
export const getMenuItemsByPosition = (position: 'main' | 'bottom') => {
  return MENU_ITEMS.filter((item) => !item.hidden && item.position === position)
}
