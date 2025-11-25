import { LucideIcon, Clock, BookOpen, CheckSquare, NotebookPen, BarChart, Settings, MessageSquare } from 'lucide-react'

export interface MenuItem {
  id: string
  labelKey: string // i18n translation key
  icon: LucideIcon
  path: string
  position?: 'main' | 'bottom' // Menu position
  badge?: number // Optional badge count
  hidden?: boolean // Whether the item is hidden
  parentId?: string // Parent menu ID (for nesting)
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
    id: 'ai-summary-knowledge',
    labelKey: 'menu.aiSummaryKnowledge',
    icon: BookOpen,
    path: '/insights/knowledge',
    position: 'main'
  },
  {
    id: 'ai-summary-todos',
    labelKey: 'menu.aiSummaryTodos',
    icon: CheckSquare,
    path: '/insights/todos',
    position: 'main'
  },
  {
    id: 'ai-summary-diary',
    labelKey: 'menu.aiSummaryDiary',
    icon: NotebookPen,
    path: '/insights/diary',
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

// Group menu items by position
export const getMenuItemsByPosition = (position: 'main' | 'bottom') => {
  return MENU_ITEMS.filter((item) => !item.hidden && item.position === position)
}
