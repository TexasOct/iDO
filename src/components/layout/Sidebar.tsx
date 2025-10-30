import { cn } from '@/lib/utils'
import { MenuItem } from '@/lib/config/menu'
import { MenuButton } from '@/components/shared/MenuButton'
import { useUIStore } from '@/lib/stores/ui'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/system/theme/theme-toggle'
import { LanguageToggle } from '@/components/system/language/language-toggle'
import { useTranslation } from 'react-i18next'

interface SidebarProps {
  collapsed: boolean
  mainItems: MenuItem[]
  bottomItems: MenuItem[]
  activeItemId: string
  onMenuClick: (menuId: string, path: string) => void
}

export function Sidebar({ collapsed, mainItems, bottomItems, activeItemId, onMenuClick }: SidebarProps) {
  // 分别订阅各个字段，避免选择器返回新对象
  const toggleSidebar = useUIStore((state) => state.toggleSidebar)
  const badges = useUIStore((state) => state.badges)
  const { t } = useTranslation()

  return (
    <aside
      className={cn('bg-card flex flex-col border-r transition-all duration-200', collapsed ? 'w-[76px]' : 'w-64')}>
      {/* 顶部空间预留（系统窗口控制按钮） */}
      <div className="h-5" />

      {/* Logo 区域 */}
      <div className={cn('flex h-16 items-center border-b px-4', collapsed ? 'justify-center' : 'justify-start')}>
        {!collapsed && <h1 className="text-lg font-semibold">Rewind</h1>}
      </div>

      {/* 主菜单区域 */}
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {mainItems.map((item) => (
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

      {/* 底部菜单区域 */}
      <div className="space-y-1 border-t p-2">
        {/* 主题和语言切换器 */}
        <div className={cn('flex flex-col gap-2 px-1 py-2', collapsed ? 'items-center' : 'px-3')}>
          {/* 折叠/展开按钮 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleSidebar}
            className={cn(
              'relative flex w-full items-center overflow-hidden transition-all duration-200',
              collapsed ? 'justify-center' : 'justify-start'
            )}>
            {/* 展开状态的内容 */}
            <div
              className={cn(
                'flex items-center gap-2 whitespace-nowrap transition-all duration-200',
                collapsed && '-translate-x-8 opacity-0'
              )}>
              <ChevronLeft className="h-5 w-5 flex-shrink-0" />
              <span>{t('common.collapse')}</span>
            </div>

            {/* 收缩状态的图标 */}
            <ChevronRight
              className={cn('absolute h-5 w-5 transition-all duration-200', !collapsed && 'translate-x-8 opacity-0')}
            />
          </Button>
          {collapsed ? (
            // 折叠状态：只显示按钮
            <>
              <ThemeToggle />
              <LanguageToggle />
            </>
          ) : (
            // 展开状态：标题 + 按钮
            <>
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground text-xs font-medium">{t('settings.theme')}</span>
                <ThemeToggle />
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground text-xs font-medium">{t('common.language')}</span>
                <LanguageToggle />
              </div>
            </>
          )}
        </div>
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
