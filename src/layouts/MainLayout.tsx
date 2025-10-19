import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router'
import { useUIStore } from '@/lib/stores/ui'
import { MENU_ITEMS, getMenuItemsByPosition } from '@/lib/config/menu'
import { Sidebar } from '@/components/layout/Sidebar'
import { DragRegion } from '@/components/layout/DragRegion'

export function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { activeMenuItem, setActiveMenuItem, sidebarCollapsed } = useUIStore()

  // 路由变化时同步 UI 状态
  useEffect(() => {
    const currentPath = location.pathname
    const matchedItem = MENU_ITEMS.find((item) => item.path === currentPath)
    if (matchedItem && matchedItem.id !== activeMenuItem) {
      setActiveMenuItem(matchedItem.id as any)
    }
  }, [location.pathname, activeMenuItem, setActiveMenuItem])

  // 菜单点击处理
  const handleMenuClick = (menuId: string, path: string) => {
    setActiveMenuItem(menuId as any)
    navigate(path)
  }

  const mainMenuItems = getMenuItemsByPosition('main')
  const bottomMenuItems = getMenuItemsByPosition('bottom')

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      {/* 顶部悬浮拖拽区域 */}
      <DragRegion />

      <div className="flex flex-1 overflow-hidden">
        {/* 左侧菜单栏 */}
        <Sidebar
          collapsed={sidebarCollapsed}
          mainItems={mainMenuItems}
          bottomItems={bottomMenuItems}
          activeItemId={activeMenuItem}
          onMenuClick={handleMenuClick}
        />

        {/* 右侧内容区域 - 悬浮容器 */}
        <main className="flex-1 overflow-hidden rounded-2xl bg-card border border-black/10 dark:border-white/10 m-2">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
