import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface MenuButtonProps {
  icon: LucideIcon
  label: string
  active?: boolean
  collapsed?: boolean
  badge?: number
  onClick?: () => void
  className?: string
}

export function MenuButton({ icon: Icon, label, active, collapsed, badge, onClick, className }: MenuButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 transition-all',
        'hover:bg-accent hover:text-accent-foreground',
        active && 'bg-accent text-accent-foreground font-medium',
        collapsed && 'justify-center',
        className
      )}
      title={collapsed ? label : undefined}>
      <Icon className="h-5 w-5 flex-shrink-0" />

      {!collapsed && <span className="flex-1 truncate text-left">{label}</span>}

      {/* 角标 */}
      {badge !== undefined && badge > 0 && (
        <Badge
          variant="destructive"
          className={cn('h-5 min-w-[20px] px-1 text-xs', collapsed && 'absolute -top-1 -right-1')}>
          {badge > 99 ? '99+' : badge}
        </Badge>
      )}
    </button>
  )
}
