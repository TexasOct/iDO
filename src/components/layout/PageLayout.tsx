import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface PageLayoutProps {
  children: ReactNode
  className?: string
}

/**
 * Page layout container
 * Provides a unified layout structure
 */
export function PageLayout({ children, className }: PageLayoutProps) {
  return <div className={cn('flex h-full flex-col', className)}>{children}</div>
}
