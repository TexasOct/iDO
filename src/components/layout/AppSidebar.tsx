import { MenuItem } from '@/lib/config/menu'
import { useUIStore } from '@/lib/stores/ui'
import { useTranslation } from 'react-i18next'
import { useMemo } from 'react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger
} from '@/components/ui/sidebar'
import { SystemStatusIndicator } from '@/components/system/SystemStatusIndicator'

interface AppSidebarProps {
  mainItems: MenuItem[]
  bottomItems: MenuItem[]
  activeItemId: string
  onMenuClick: (menuId: string, path: string) => void
}

export function AppSidebar({ mainItems, bottomItems, activeItemId, onMenuClick }: AppSidebarProps) {
  const badges = useUIStore((state) => state.badges)
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
    <Sidebar collapsible="icon">
      {/* 顶部空间预留（系统窗口控制按钮） */}
      <div className="h-5" />

      <SidebarHeader>
        <div className="flex items-center gap-2 px-0.5">
          <SidebarTrigger />
          <h1 className="text-lg font-semibold group-data-[collapsible=icon]:hidden">iDO</h1>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainItems.map((item) => {
                const isActive = activeTrail.has(item.id)
                const Icon = item.icon
                const badge = badges[item.id]

                return (
                  <SidebarMenuItem key={item.id}>
                    <SidebarMenuButton
                      isActive={isActive}
                      onClick={() => onMenuClick(item.id, item.path)}
                      tooltip={t(item.labelKey as any)}
                      className={item.parentId ? 'pl-9' : undefined}>
                      <Icon className="size-5" />
                      <span className="flex-1 truncate">{t(item.labelKey as any)}</span>
                      {badge && badge > 0 ? (
                        <span className="bg-primary text-primary-foreground ml-auto flex size-5 items-center justify-center rounded-full text-xs">
                          {badge}
                        </span>
                      ) : null}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          {/* System Status Indicator */}
          <SidebarMenuItem>
            <SystemStatusIndicator showMenu />
          </SidebarMenuItem>

          {bottomItems.map((item) => {
            const isActive = activeItemId === item.id
            const Icon = item.icon
            const badge = badges[item.id]

            return (
              <SidebarMenuItem key={item.id}>
                <SidebarMenuButton
                  isActive={isActive}
                  onClick={() => onMenuClick(item.id, item.path)}
                  tooltip={t(item.labelKey as any)}>
                  <Icon className="size-5" />
                  <span className="flex-1 truncate">{t(item.labelKey as any)}</span>
                  {badge && badge > 0 ? (
                    <span className="bg-primary text-primary-foreground ml-auto flex size-5 items-center justify-center rounded-full text-xs">
                      {badge}
                    </span>
                  ) : null}
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
