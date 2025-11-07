import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router'
import { useUIStore } from '@/lib/stores/ui'
import { MENU_ITEMS, getMenuItemsByPosition } from '@/lib/config/menu'
import { Sidebar } from '@/components/layout/Sidebar'
import { FloatingStatusBall } from '@/components/system/FloatingStatusBall'

export function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  // 分别订阅各个字段，避免选择器返回新对象
  const activeMenuItem = useUIStore((state) => state.activeMenuItem)
  const setActiveMenuItem = useUIStore((state) => state.setActiveMenuItem)
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed)

  // 路由变化时同步 UI 状态
  useEffect(() => {
    const currentPath = location.pathname
    const matchedItem = [...MENU_ITEMS].reverse().find((item) => item.path === currentPath)
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
        <main className="bg-card m-2 flex-1 overflow-y-auto rounded-2xl border border-black/10 dark:border-white/10">
          <Outlet />
        </main>
      </div>

      {/* 右下角悬浮状态球 */}
      <FloatingStatusBall />
    </div>
  )
}
