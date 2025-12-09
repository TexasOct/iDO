import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Activity } from '@/lib/types/activity'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Loader2, Split, Clock, Layers } from 'lucide-react'
import { format } from 'date-fns'
import { toast } from 'sonner'
import { splitActivityHandler } from '@/lib/client/apiClient'

interface SplitActivityDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  activity: Activity | null
  events: Array<{ id: string; title: string; startTime: number; endTime: number }>
  onSplitSuccess?: () => void
}

interface SplitGroup {
  id: string
  name: string
  eventIds: Set<string>
}

export function SplitActivityDialog({
  open,
  onOpenChange,
  activity,
  events,
  onSplitSuccess
}: SplitActivityDialogProps) {
  const { t } = useTranslation()
  const [splitting, setSplitting] = useState(false)

  // Initialize two split groups
  const [splitGroups, setSplitGroups] = useState<SplitGroup[]>([
    { id: 'group-1', name: 'Group 1', eventIds: new Set() },
    { id: 'group-2', name: 'Group 2', eventIds: new Set() }
  ])

  // Sort events by time
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => a.startTime - b.startTime)
  }, [events])

  const handleToggleEvent = (eventId: string, groupId: string) => {
    setSplitGroups((prev) =>
      prev.map((group) => {
        const newEventIds = new Set(group.eventIds)
        if (group.id === groupId) {
          // Toggle event in this group
          if (newEventIds.has(eventId)) {
            newEventIds.delete(eventId)
          } else {
            newEventIds.add(eventId)
          }
        } else {
          // Remove from other groups
          newEventIds.delete(eventId)
        }
        return { ...group, eventIds: newEventIds }
      })
    )
  }

  const handleAddGroup = () => {
    const newGroupId = `group-${splitGroups.length + 1}`
    setSplitGroups((prev) => [
      ...prev,
      { id: newGroupId, name: `Group ${splitGroups.length + 1}`, eventIds: new Set() }
    ])
  }

  const handleRemoveGroup = (groupId: string) => {
    if (splitGroups.length <= 2) {
      toast.error(t('activity.mustHaveTwoGroups'))
      return
    }
    setSplitGroups((prev) => prev.filter((g) => g.id !== groupId))
  }

  const handleSplit = async () => {
    if (!activity) {
      toast.error(t('activity.noActivitySelected'))
      return
    }

    // Validate: each group must have at least one event
    const validGroups = splitGroups.filter((g) => g.eventIds.size > 0)
    if (validGroups.length < 2) {
      toast.error(t('activity.eachGroupNeedsEvents'))
      return
    }

    // Validate: all events must be assigned
    const assignedEvents = new Set<string>()
    validGroups.forEach((g) => g.eventIds.forEach((id) => assignedEvents.add(id)))
    if (assignedEvents.size !== events.length) {
      toast.error(t('activity.allEventsMustBeAssigned'))
      return
    }

    setSplitting(true)

    try {
      // Create event ID to index mapping
      const eventIdToIndex = new Map<string, number>()
      events.forEach((event, index) => {
        eventIdToIndex.set(event.id, index + 1) // 1-based index
      })

      // Prepare split points
      const splitPoints = validGroups.map((group) => {
        const groupEvents = sortedEvents.filter((e) => group.eventIds.has(e.id))
        const eventIndexes = Array.from(group.eventIds)
          .map((id) => eventIdToIndex.get(id))
          .filter((idx): idx is number => idx !== undefined)
          .sort((a, b) => a - b)

        return {
          title: group.name,
          description: groupEvents.length > 0 ? `Split from ${activity.title}` : '',
          eventIndexes
        }
      })

      // Call backend split API with correct structure
      const response = await splitActivityHandler({
        activityId: activity.id,
        splitPoints
      })

      if (!response?.success) {
        console.error('[SplitActivityDialog] Split failed:', response?.error)
        toast.error('Failed to split activity')
        return
      }

      toast.success(`Successfully split activity into ${validGroups.length} parts`)
      onOpenChange(false)
      onSplitSuccess?.()
    } catch (error) {
      console.error('[SplitActivityDialog] Split failed:', error)
      toast.error('Failed to split activity')
    } finally {
      setSplitting(false)
    }
  }

  const handleCancel = () => {
    if (splitting) return
    onOpenChange(false)
  }

  // Calculate statistics for each group
  const groupStats = useMemo(() => {
    return splitGroups.map((group) => {
      const groupEvents = sortedEvents.filter((e) => group.eventIds.has(e.id))
      if (groupEvents.length === 0) {
        return { eventCount: 0, startTime: 0, endTime: 0, duration: 0 }
      }

      const startTime = groupEvents[0].startTime
      const endTime = groupEvents[groupEvents.length - 1].endTime
      const duration = endTime - startTime

      return { eventCount: groupEvents.length, startTime, endTime, duration }
    })
  }, [splitGroups, sortedEvents])

  if (!activity) {
    return null
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Split className="h-5 w-5" />
            Split Activity
          </DialogTitle>
          <DialogDescription>
            Split "{activity.title}" into {splitGroups.length} separate activities
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Activity info */}
          <div className="border-border bg-muted/30 rounded-md border p-3">
            <div className="space-y-1 text-sm">
              <div className="text-foreground font-medium">{activity.title}</div>
              {activity.description && <div className="text-muted-foreground text-xs">{activity.description}</div>}
              <div className="text-muted-foreground flex items-center gap-2 text-xs">
                <Clock className="h-3 w-3" />
                <span>{format(new Date(activity.startTime), 'HH:mm:ss')}</span>
                <span>-</span>
                <span>{format(new Date(activity.endTime), 'HH:mm:ss')}</span>
                <span>·</span>
                <span>{events.length} events</span>
              </div>
            </div>
          </div>

          {/* Split groups */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Split into Groups</Label>
              <Button variant="outline" size="sm" onClick={handleAddGroup} disabled={splitting} className="h-7 text-xs">
                Add Group
              </Button>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              {splitGroups.map((group, groupIndex) => {
                const stats = groupStats[groupIndex]
                const durationMinutes = Math.floor(stats.duration / (1000 * 60))

                return (
                  <div key={group.id} className="border-border bg-card space-y-2 rounded-md border p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Layers className="text-primary h-4 w-4" />
                        <span className="text-sm font-medium">{group.name}</span>
                      </div>
                      {splitGroups.length > 2 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveGroup(group.id)}
                          disabled={splitting}
                          className="text-destructive hover:text-destructive h-6 px-2 text-xs">
                          Remove
                        </Button>
                      )}
                    </div>

                    {/* Group stats */}
                    {stats.eventCount > 0 && (
                      <div className="bg-primary/5 text-muted-foreground rounded-sm p-2 text-xs">
                        <div className="flex items-center gap-2">
                          <Clock className="h-3 w-3" />
                          <span>
                            {format(new Date(stats.startTime), 'HH:mm:ss')} -{' '}
                            {format(new Date(stats.endTime), 'HH:mm:ss')}
                          </span>
                        </div>
                        <div className="mt-1">
                          {stats.eventCount} events · {durationMinutes}m
                        </div>
                      </div>
                    )}

                    {/* Events in this group */}
                    <div className="space-y-1">
                      {sortedEvents.map((event) => {
                        const isChecked = group.eventIds.has(event.id)
                        return (
                          <div
                            key={event.id}
                            className={`flex items-start gap-2 rounded-sm p-2 transition-colors ${
                              isChecked ? 'bg-primary/10' : 'hover:bg-muted/50'
                            }`}>
                            <Checkbox
                              id={`${group.id}-${event.id}`}
                              checked={isChecked}
                              onCheckedChange={() => handleToggleEvent(event.id, group.id)}
                              disabled={splitting}
                              className="mt-0.5"
                            />
                            <label htmlFor={`${group.id}-${event.id}`} className="flex-1 cursor-pointer text-xs">
                              <div className="text-foreground font-medium">{event.title}</div>
                              <div className="text-muted-foreground mt-0.5">
                                {format(new Date(event.startTime), 'HH:mm:ss')}
                              </div>
                            </label>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Summary */}
          <div className="border-primary/30 bg-primary/5 text-muted-foreground rounded-md border p-3 text-xs">
            <div className="text-primary font-medium">Split Summary</div>
            <div className="mt-1">
              Activity will be split into {splitGroups.filter((g) => g.eventIds.size > 0).length} parts
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={splitting}>
            Cancel
          </Button>
          <Button onClick={handleSplit} disabled={splitting}>
            {splitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Split Activity
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
