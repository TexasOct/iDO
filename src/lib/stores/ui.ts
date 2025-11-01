import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type MenuItemId = 'activity' | 'recent-events' | 'ai-summary' | 'dashboard' | 'agents' | 'settings' | 'chat'

interface UIState {
  // 当前激活的菜单项（与路由同步）
  activeMenuItem: MenuItemId

  // 侧边栏是否折叠
  sidebarCollapsed: boolean

  // 通知角标数据
  badges: Record<string, number>

  // Actions
  setActiveMenuItem: (item: MenuItemId) => void
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setBadge: (menuId: string, count: number) => void
  clearBadge: (menuId: string) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
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
    }),
    {
      name: 'rewind-ui-state',
      // 只持久化部分状态
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed
      })
    }
  )
)
