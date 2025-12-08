import * as React from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, checked, onCheckedChange, disabled, ...props }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      onCheckedChange?.(e.target.checked)
    }

    return (
      <div className="relative inline-flex">
        <input
          type="checkbox"
          ref={ref}
          checked={checked}
          onChange={handleChange}
          disabled={disabled}
          className={cn(
            'peer border-primary ring-offset-background h-4 w-4 shrink-0 appearance-none rounded-sm border transition-colors',
            'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'checked:bg-primary checked:text-primary-foreground',
            className
          )}
          {...props}
        />
        {checked && (
          <div className="text-primary-foreground pointer-events-none absolute inset-0 flex items-center justify-center">
            <Check className="h-3 w-3" />
          </div>
        )}
      </div>
    )
  }
)

Checkbox.displayName = 'Checkbox'

export { Checkbox }
