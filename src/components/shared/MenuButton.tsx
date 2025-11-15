import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface MenuButtonProps {
  icon: LucideIcon
  label: string
  active?: boolean
  collapsed?: boolean
  badge?: number
  onClick?: () => void
  className?: string
}

export function MenuButton({ icon: Icon, label, active, collapsed, onClick, className }: MenuButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'relative flex h-10 w-full items-center rounded-lg transition-all',
        'hover:bg-accent hover:text-accent-foreground',
        active && 'bg-accent text-accent-foreground font-medium',
        collapsed ? 'justify-center px-0' : 'gap-3 px-3',
        className
      )}
      title={collapsed ? label : undefined}>
      <Icon className="h-5 w-5 shrink-0" />

      <span
        className={cn(
          'truncate text-left transition-opacity duration-200',
          collapsed ? 'pointer-events-none absolute opacity-0' : 'flex-1 opacity-100'
        )}>
        {label}
      </span>
    </button>
  )
}
