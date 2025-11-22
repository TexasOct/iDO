import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router'
import { useUIStore } from '@/lib/stores/ui'
import { useSetupStore } from '@/lib/stores/setup'
import { MENU_ITEMS, getMenuItemsByPosition } from '@/lib/config/menu'
import { AppSidebar } from '@/components/layout/AppSidebar'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'

export function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  // Subscribe to individual fields to avoid selector churn
  const activeMenuItem = useUIStore((state) => state.activeMenuItem)
  const setActiveMenuItem = useUIStore((state) => state.setActiveMenuItem)
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed)

  // Check if setup is active
  const isSetupActive = useSetupStore((state) => state.isActive)
  const hasAcknowledged = useSetupStore((state) => state.hasAcknowledged)
  const shouldShowSetup = isSetupActive && !hasAcknowledged

  // Sync UI state when the route changes
  useEffect(() => {
    const currentPath = location.pathname
    const matchedItem = [...MENU_ITEMS].reverse().find((item) => item.path === currentPath)
    if (matchedItem && matchedItem.id !== activeMenuItem) {
      setActiveMenuItem(matchedItem.id as any)
    }
  }, [location.pathname, activeMenuItem, setActiveMenuItem])

  // Menu click handler
  const handleMenuClick = (menuId: string, path: string) => {
    setActiveMenuItem(menuId as any)
    navigate(path)
  }

  const mainMenuItems = getMenuItemsByPosition('main')
  const bottomMenuItems = getMenuItemsByPosition('bottom')

  return (
    <SidebarProvider open={!sidebarCollapsed} onOpenChange={(open) => useUIStore.getState().setSidebarCollapsed(!open)}>
      <div className="flex h-screen w-screen overflow-hidden">
        {/* Left sidebar (hidden during setup flow) */}
        {!shouldShowSetup && (
          <AppSidebar
            mainItems={mainMenuItems}
            bottomItems={bottomMenuItems}
            activeItemId={activeMenuItem}
            onMenuClick={handleMenuClick}
          />
        )}

        {/* Right content area */}
        <SidebarInset className="flex flex-col">
          <main className="mb-1 flex-1 overflow-y-auto">
            <Outlet />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  )
}
