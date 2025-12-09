import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useSetupStore } from '@/lib/stores/setup'

/**
 * Development-only keyboard shortcuts for testing
 * Only active when import.meta.env.DEV is true
 */
export function useDevShortcuts() {
  const { t } = useTranslation()

  useEffect(() => {
    if (!import.meta.env.DEV) {
      return
    }

    const handleKeyPress = (event: KeyboardEvent) => {
      // Ctrl/Cmd + Alt + R: Reset welcome flow (changed to avoid browser refresh conflict)
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'r') {
        event.preventDefault()
        useSetupStore.getState().reset()
        toast.success(t('debug.welcomeFlowReset'), {
          description: 'The setup has been reset to the welcome screen'
        })
        return
      }

      // Ctrl/Cmd + Alt + O: Reopen current step
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'o') {
        event.preventDefault()
        const { isActive, currentStep } = useSetupStore.getState()
        if (isActive) {
          toast.info(t('debug.setupAlreadyActive'), {
            description: `Current step: ${currentStep}`
          })
        } else {
          useSetupStore.getState().reopen()
          toast.success(t('debug.setupReopened'), {
            description: `Showing step: ${currentStep}`
          })
        }
        return
      }

      // Ctrl/Cmd + Alt + S: Show setup state
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 's') {
        event.preventDefault()
        const state = useSetupStore.getState()
        console.log('📋 Setup State:', {
          isActive: state.isActive,
          hasAcknowledged: state.hasAcknowledged,
          currentStep: state.currentStep
        })
        toast.info(t('debug.setupStateLogged'), {
          description: `Step: ${state.currentStep} | Active: ${state.isActive}`
        })
        return
      }

      // Ctrl/Cmd + Alt + 1-5: Jump to specific step
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && ['1', '2', '3', '4', '5'].includes(event.key)) {
        event.preventDefault()
        const stepMap: Record<string, 'welcome' | 'screens' | 'model' | 'permissions' | 'complete'> = {
          '1': 'welcome',
          '2': 'screens',
          '3': 'model',
          '4': 'permissions',
          '5': 'complete'
        }
        const step = stepMap[event.key]
        useSetupStore.getState().goToStep(step)
        toast.success(`⚡ Jumped to step: ${step}`, {
          description: 'The setup flow is now showing this step'
        })
        return
      }
    }

    document.addEventListener('keydown', handleKeyPress)

    // Log available shortcuts on mount
    console.log(`
🎯 Developer Shortcuts Available:
  Cmd/Ctrl + Shift + R  →  Reset welcome flow
  Cmd/Ctrl + Shift + O  →  Reopen current step
  Cmd/Ctrl + Shift + S  →  Show setup state
  Cmd/Ctrl + Shift + 1  →  Jump to Welcome
  Cmd/Ctrl + Shift + 2  →  Jump to Screen Selection
  Cmd/Ctrl + Shift + 3  →  Jump to Model Setup
  Cmd/Ctrl + Shift + 4  →  Jump to Permissions
  Cmd/Ctrl + Shift + 5  →  Jump to Complete
    `)

    return () => {
      document.removeEventListener('keydown', handleKeyPress)
    }
  }, [t])
}
