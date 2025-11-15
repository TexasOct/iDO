import { cn } from '@/lib/utils'
import { MenuItem } from '@/lib/config/menu'
import { MenuButton } from '@/components/shared/MenuButton'
import { useUIStore } from '@/lib/stores/ui'
import { useTranslation } from 'react-i18next'
import { useMemo } from 'react'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SidebarProps {
  collapsed: boolean
  mainItems: MenuItem[]
  bottomItems: MenuItem[]
  activeItemId: string
  onMenuClick: (menuId: string, path: string) => void
}

export function Sidebar({ collapsed, mainItems, bottomItems, activeItemId, onMenuClick }: SidebarProps) {
  // 分别订阅各个字段，避免选择器返回新对象
  const badges = useUIStore((state) => state.badges)
  const toggleSidebar = useUIStore((state) => state.toggleSidebar)
  const { t } = useTranslation()

  const itemsById = useMemo(() => new Map(mainItems.map((item) => [item.id, item])), [mainItems])

  const activeTrail = useMemo(() => {
    const trail = new Set<string>()
    if (!activeItemId) return trail

    let currentId: string | undefined = activeItemId
    while (currentId) {
      trail.add(currentId)
      const next = itemsById.get(currentId)
      if (next?.parentId) {
        currentId = next.parentId
      } else {
        break
      }
    }

    return trail
  }, [activeItemId, itemsById])

  return (
    <aside className={cn('bg-card flex flex-col transition-all duration-200', collapsed ? 'w-[65px]' : 'w-66')}>
      {/* 顶部空间预留（系统窗口控制按钮） */}
      <div className="h-5" />

      {/* Logo 区域 + 菜单按钮 */}
      <div className="flex h-16 items-center justify-start gap-3 px-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="h-8 w-8 shrink-0"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          <Menu className="h-4 w-4" />
        </Button>
        <h1
          className={cn(
            'text-lg font-semibold transition-opacity duration-200',
            collapsed ? 'pointer-events-none opacity-0' : 'opacity-100'
          )}>
          iDO
        </h1>
      </div>

      {/* 主菜单区域 */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-1 p-2">
          {mainItems.map((item) => {
            const isActive = activeTrail.has(item.id)
            const indentClass = !collapsed && item.parentId ? 'pl-9 pr-3' : undefined

            return (
              <MenuButton
                key={item.id}
                icon={item.icon}
                label={t(item.labelKey as any)}
                active={isActive}
                collapsed={collapsed}
                badge={badges[item.id]}
                onClick={() => onMenuClick(item.id, item.path)}
                className={indentClass}
              />
            )
          })}
        </div>
      </div>

      {/* 底部菜单区域 */}
      <div className="space-y-1 p-2">
        {bottomItems.map((item) => (
          <MenuButton
            key={item.id}
            icon={item.icon}
            label={t(item.labelKey as any)}
            active={activeItemId === item.id}
            collapsed={collapsed}
            badge={badges[item.id]}
            onClick={() => onMenuClick(item.id, item.path)}
          />
        ))}
      </div>
    </aside>
  )
}
