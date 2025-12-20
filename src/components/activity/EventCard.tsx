import { Event } from '@/lib/types/activity'
import { TimeDisplay } from '@/components/shared/TimeDisplay'
import { ChevronDown, ChevronRight, Clock } from 'lucide-react'

interface EventCardProps {
  event: Event
  isExpanded: boolean
  onToggleExpand: () => void
  onViewActions?: () => void
  actionsCount?: number
}

export function EventCard({
  event,
  isExpanded,
  onToggleExpand,
  onViewActions: _onViewActions,
  actionsCount = 0
}: EventCardProps) {
  const duration = event.endTime - event.startTime
  const durationMinutes = Math.floor(duration / 60000)
  const durationSeconds = Math.floor((duration % 60000) / 1000)

  return (
    <div className="border-border bg-card relative rounded-lg border p-4 transition-all hover:shadow-md">
      {/* Header section with flex layout */}
      <div className="flex items-start gap-3">
        {/* Title - takes up remaining space and wraps */}
        <div className="min-w-0 flex-1">
          <h4 className="text-foreground leading-relaxed font-medium break-words">{event.title}</h4>
        </div>

        {/* Time range and expand button - takes up actual space */}
        <div className="flex shrink-0 items-center gap-2">
          <div className="text-muted-foreground flex items-center gap-2 text-xs whitespace-nowrap">
            <Clock className="h-3 w-3" />
            <TimeDisplay timestamp={event.startTime} />
            <span>-</span>
            <TimeDisplay timestamp={event.endTime} />
          </div>

          <button
            onClick={onToggleExpand}
            className="hover:bg-accent rounded p-1 transition-colors"
            aria-label={isExpanded ? 'Collapse' : 'Expand'}>
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Description section - occupies full width below */}
      {event.description && <p className="text-muted-foreground mt-3 text-sm leading-relaxed">{event.description}</p>}

      {/* Duration and Actions Count */}
      <div className="text-muted-foreground mt-3 flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>
            {durationMinutes > 0 && `${durationMinutes}m `}
            {durationSeconds > 0 && `${durationSeconds}s`}
          </span>
        </div>

        {actionsCount > 0 && (
          <div className="flex items-center gap-1">
            <span>{actionsCount} actions</span>
          </div>
        )}
      </div>

      {/* View Actions Button */}
      {/*{isExpanded && onViewActions && actionsCount > 0 && (
        <div className="mt-3">
          <button
            onClick={onViewActions}
            className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground transition-colors hover:bg-primary/90"
          >
            View Actions ({actionsCount})
          </button>
        </div>
      )}*/}

      {/* Expanded Content Placeholder */}
      {isExpanded && (
        <div className="border-border mt-3 border-t pt-3">
          <p className="text-muted-foreground text-xs">Event Details</p>

          {/* Source Actions */}
          {event.sourceActionIds && event.sourceActionIds.length > 0 && (
            <div className="text-muted-foreground mt-2 text-xs">
              <span className="font-medium">Source Actions:</span>
              <span className="ml-1">{event.sourceActionIds.length}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
