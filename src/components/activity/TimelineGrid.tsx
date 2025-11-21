import { format } from 'date-fns'

interface TimelineGridProps {
  startHour?: number
  endHour?: number
  children?: React.ReactNode
}

/**
 * Timeline grid component that displays hourly time slots
 * Creates a calendar-style timeline view with horizontal time slots
 */
export function TimelineGrid({ startHour = 0, endHour = 24, children }: TimelineGridProps) {
  const hours = Array.from({ length: endHour - startHour }, (_, i) => startHour + i)

  return (
    <div className="relative h-full overflow-y-auto">
      {/* Timeline grid */}
      <div className="relative min-h-full">
        {hours.map((hour) => (
          <div key={hour} className="border-border/40 relative h-16 border-b last:border-b-0">
            {/* Time label */}
            <div className="text-muted-foreground absolute top-0 left-0 w-20 p-2 text-sm font-medium">
              {format(new Date().setHours(hour, 0, 0, 0), 'HH:mm')}
            </div>
            {/* Content area */}
            <div className="ml-20 h-full" />
          </div>
        ))}
        {/* Activity blocks overlay */}
        {children}
      </div>
    </div>
  )
}
