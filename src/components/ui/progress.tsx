import * as React from 'react'
import { cn } from '@/lib/utils'

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(({ className, value = 0, ...props }, ref) => {
  const percentage = Math.min(Math.max(value, 0), 100)

  return (
    <div
      ref={ref}
      className={cn('bg-secondary relative h-4 w-full overflow-hidden rounded-full', className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percentage}
      {...props}>
      <div className="bg-primary h-full transition-all duration-300 ease-in-out" style={{ width: `${percentage}%` }} />
    </div>
  )
})

Progress.displayName = 'Progress'

export { Progress }
