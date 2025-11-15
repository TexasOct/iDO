import { Bug, RotateCcw, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { useSetupStore } from '@/lib/stores/setup'

export function DeveloperSettings() {
  // const [isExpanded, setIsExpanded] = useState(false)

  const isActive = useSetupStore((state) => state.isActive)
  const hasAcknowledged = useSetupStore((state) => state.hasAcknowledged)
  const currentStep = useSetupStore((state) => state.currentStep)
  const reset = useSetupStore((state) => state.reset)
  const reopen = useSetupStore((state) => state.reopen)

  const handleResetSetup = () => {
    reset()
    toast.success('Welcome flow has been reset')
  }

  const handleReopenSetup = () => {
    reopen()
    toast.success('Welcome flow reopened')
  }

  const handleClearLocalStorage = () => {
    if (window.confirm('This will clear ALL local storage data. Continue?')) {
      localStorage.clear()
      toast.success('Local storage cleared. Reload the page to see changes.')
    }
  }

  return (
    <Card>
      <CardHeader className="pb-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bug className="h-5 w-5" />
            <div>
              <CardTitle>Developer Tools</CardTitle>
              <CardDescription>Testing utilities for development</CardDescription>
            </div>
          </div>
          <Badge variant="outline" className="text-xs">
            DEV ONLY
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 border-t pt-6">
        {/* Welcome Flow Testing */}
        <div className="space-y-4">
          <div>
            <Label className="text-base font-semibold">Welcome Flow Testing</Label>
            <p className="text-muted-foreground mt-1 text-sm">
              Test the initial setup flow without manually clearing browser storage
            </p>
          </div>

          {/* Current State Display */}
          <div className="bg-muted/50 rounded-lg border p-4">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status:</span>
                <span className="font-medium">{isActive ? 'Active' : 'Inactive'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Acknowledged:</span>
                <span className="font-medium">{hasAcknowledged ? 'Yes' : 'No'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Current Step:</span>
                <span className="font-medium">{currentStep}</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" size="sm" onClick={handleResetSetup} className="gap-2">
              <RotateCcw className="h-4 w-4" />
              Reset to Welcome
            </Button>

            <Button variant="outline" size="sm" onClick={handleReopenSetup} className="gap-2" disabled={isActive}>
              <RotateCcw className="h-4 w-4" />
              Reopen Current Step
            </Button>
          </div>

          <div className="text-muted-foreground rounded-lg bg-blue-500/10 p-3 text-xs">
            <strong>Tip:</strong> Use "Reset to Welcome" to restart the entire flow from step 1. Use "Reopen Current
            Step" to show the overlay at the current step without resetting progress.
          </div>
        </div>

        {/* Storage Management */}
        <div className="space-y-4 border-t pt-4">
          <div>
            <Label className="text-base font-semibold">Storage Management</Label>
            <p className="text-muted-foreground mt-1 text-sm">Clear browser storage (use with caution)</p>
          </div>

          <Button variant="destructive" size="sm" onClick={handleClearLocalStorage} className="gap-2">
            <Trash2 className="h-4 w-4" />
            Clear All Local Storage
          </Button>

          <div className="text-muted-foreground rounded-lg bg-yellow-500/10 p-3 text-xs">
            <strong>Warning:</strong> This will clear ALL persisted data including settings, models, and user
            preferences. You'll need to reload the page afterwards.
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
