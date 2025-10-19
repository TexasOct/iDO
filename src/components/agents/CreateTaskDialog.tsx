import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAgentsStore } from '@/lib/stores/agents'
import { AgentType } from '@/lib/types/agents'
import { useTranslation } from 'react-i18next'

interface CreateTaskDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateTaskDialog({ open, onOpenChange }: CreateTaskDialogProps) {
  const { t } = useTranslation()
  const { availableAgents, createTask } = useAgentsStore()
  const [selectedAgent, setSelectedAgent] = useState<AgentType | ''>('')
  const [planDescription, setPlanDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedAgent || !planDescription.trim()) {
      return
    }

    setIsSubmitting(true)
    try {
      await createTask(selectedAgent, planDescription)
      // 重置表单
      setSelectedAgent('')
      setPlanDescription('')
      onOpenChange(false)
    } catch (error) {
      console.error('Failed to create task:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{t('agents.createNewTask')}</DialogTitle>
            <DialogDescription>{t('agents.createTaskDescription')}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="agent">{t('agents.selectAgent')}</Label>
              <Select value={selectedAgent} onValueChange={(value) => setSelectedAgent(value as AgentType)}>
                <SelectTrigger id="agent">
                  <SelectValue placeholder={t('agents.selectAgentPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {availableAgents.map((agent) => (
                    <SelectItem key={agent.name} value={agent.name}>
                      <div className="flex flex-col items-start">
                        <span className="font-medium">{agent.name}</span>
                        <span className="text-xs text-muted-foreground">{agent.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="plan">{t('agents.taskDescription')}</Label>
              <Textarea
                id="plan"
                placeholder={t('agents.taskDescriptionPlaceholder')}
                value={planDescription}
                onChange={(e) => setPlanDescription(e.target.value)}
                rows={6}
                className="resize-none"
              />
              <p className="text-xs text-muted-foreground">{t('agents.taskDescriptionTip')}</p>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={!selectedAgent || !planDescription.trim() || isSubmitting}>
              {isSubmitting ? t('agents.creating') : t('agents.createTask')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
