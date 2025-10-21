import { cn } from '@/lib/utils'
import { MenuItem } from '@/lib/config/menu'
import { MenuButton } from '@/components/shared/MenuButton'
import { useUIStore } from '@/lib/stores/ui'
import { ChevronLeft, ChevronRight, TestTube2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/system/theme/theme-toggle'
import { LanguageToggle } from '@/components/system/language/language-toggle'
import { useTranslation } from 'react-i18next'
import { greeting } from '@/lib/client/apiClient'
import { toast } from 'sonner'
import { useState } from 'react'

interface SidebarProps {
  collapsed: boolean
  mainItems: MenuItem[]
  bottomItems: MenuItem[]
  activeItemId: string
  onMenuClick: (menuId: string, path: string) => void
}

export function Sidebar({ collapsed, mainItems, bottomItems, activeItemId, onMenuClick }: SidebarProps) {
  const { toggleSidebar, badges } = useUIStore()
  const { t } = useTranslation()
  const [testing, setTesting] = useState(false)

  const handleTestPyTauri = async () => {
    setTesting(true)
    try {
      const result = await greeting({ name: 'hello' })
      console.log('PyTauri Test Result:', result)
      toast.success('PyTauri 测试成功！', {
        description: result,
        duration: 3000
      })
    } catch (error) {
      console.error('PyTauri Test Error:', error)
      toast.error('PyTauri 测试失败', {
        description: error instanceof Error ? error.message : '未知错误',
        duration: 3000
      })
    } finally {
      setTesting(false)
    }
  }

  return (
    <aside
      className={cn('bg-card flex flex-col border-r transition-all duration-200', collapsed ? 'w-[76px]' : 'w-64')}>
      {/* 顶部空间预留（系统窗口控制按钮） */}
      <div className="h-5" />

      {/* Logo 区域 */}
      <div className="flex h-14 items-center border-b px-4">
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

        {/* 主题和语言切换器 */}
        <div className={cn('flex flex-col gap-2 px-1 py-2', collapsed ? 'items-center' : 'px-3')}>
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

        {/* PyTauri 测试按钮 */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleTestPyTauri}
          disabled={testing}
          className={cn('w-full', collapsed ? 'px-2' : 'justify-start gap-2')}>
          <TestTube2 className="h-4 w-4" />
          {!collapsed && <span>{testing ? '测试中...' : '测试 PyTauri'}</span>}
        </Button>

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
      </div>
    </aside>
  )
}
