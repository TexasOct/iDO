import { create } from 'zustand'

export type MenuItemId =
  | 'activity'
  | 'recent-events'
  | 'ai-summary'
  | 'ai-summary-knowledge'
  | 'ai-summary-todos'
  | 'ai-summary-diary'
  | 'dashboard'
  | 'agents'
  | 'settings'
  | 'chat'

interface UIState {
  // Currently active menu item (kept in sync with the router)
  activeMenuItem: MenuItemId

  // Whether the sidebar is collapsed
  sidebarCollapsed: boolean

  // Notification badge data
  badges: Record<string, number>

  // Actions
  setActiveMenuItem: (item: MenuItemId) => void
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setBadge: (menuId: string, count: number) => void
  clearBadge: (menuId: string) => void
}

export const useUIStore = create<UIState>()((set) => ({
  activeMenuItem: 'activity',
  sidebarCollapsed: false,
  badges: {},

  setActiveMenuItem: (item) => set({ activeMenuItem: item }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setBadge: (menuId, count) =>
    set((state) => ({
      badges: { ...state.badges, [menuId]: count }
    })),
  clearBadge: (menuId) =>
    set((state) => {
      const { [menuId]: _, ...rest } = state.badges
      return { badges: rest }
    })
}))
