import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface PageLayoutProps {
  children: ReactNode
  className?: string
}

/**
 * 页面布局容器
 * 提供统一的布局结构
 */
export function PageLayout({ children, className }: PageLayoutProps) {
  return <div className={cn('flex h-full flex-col', className)}>{children}</div>
}
