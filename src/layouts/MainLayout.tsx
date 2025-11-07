import { useEffect, useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router'
import { useUIStore } from '@/lib/stores/ui'
import { MENU_ITEMS, getMenuItemsByPosition } from '@/lib/config/menu'
import { Sidebar } from '@/components/layout/Sidebar'
import { FloatingStatusBall } from '@/components/system/FloatingStatusBall'
import { isTauri } from '@/lib/utils/tauri'

export function MainLayout() {
  const isWindowsUA = () => {
    try {
      if (typeof navigator === 'undefined') return false
      const ua = navigator.userAgent || ''
      const plat = (navigator as any).platform || ''
      const uaDataPlat = (navigator as any).userAgentData?.platform || ''
      const s = `${ua} ${plat} ${uaDataPlat}`.toLowerCase()
      return s.includes('win')
    } catch {
      return false
    }
  }

  const [isWindows, setIsWindows] = useState<boolean>(isWindowsUA())
  const [tauriReady, setTauriReady] = useState<boolean>(typeof window !== 'undefined' && '__TAURI__' in window)
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

  // Detect Windows quickly via UA and poll for Tauri readiness (for consistency)
  useEffect(() => {
    setIsWindows(isWindowsUA())
    if (tauriReady) return
    let tries = 0
    const id = setInterval(() => {
      tries += 1
      if (typeof window !== 'undefined' && '__TAURI__' in window) {
        setTauriReady(true)
        clearInterval(id)
      } else if (tries > 20) {
        clearInterval(id)
      }
    }, 50)
    return () => clearInterval(id)
  }, [tauriReady])

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
        <main
          className={`${isWindows ? 'mt-10 mr-2 mb-2 ml-2' : 'm-2'} bg-card flex-1 overflow-y-auto rounded-2xl border border-black/10 dark:border-white/10`}>
          <Outlet />
        </main>
      </div>

      {/* 右下角悬浮状态球 */}
      <FloatingStatusBall />
    </div>
  )
}
