import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import * as apiClient from '@/lib/client/apiClient'

export type SetupStep = 'welcome' | 'model' | 'permissions' | 'complete'

interface SetupState {
  /**
   * Whether the initialization overlay is currently showing.
   * When false, the overlay stays hidden even if the step isn't complete.
   */
  isActive: boolean
  /**
   * Tracks whether the user has acknowledged the completion screen.
   * Once true we don't show the flow again unless manually reset.
   */
  hasAcknowledged: boolean
  currentStep: SetupStep

  start: () => void
  goToStep: (step: SetupStep) => void
  markModelStepDone: () => void
  markPermissionsStepDone: () => void
  completeAndAcknowledge: () => void
  skipForNow: () => void
  reopen: () => void
  reset: () => void
  checkAndActivateSetup: () => Promise<void>
}

const nextStepMap: Record<SetupStep, SetupStep> = {
  welcome: 'model',
  model: 'permissions',
  permissions: 'complete',
  complete: 'complete'
}

export const useSetupStore = create<SetupState>()(
  persist(
    (set, get) => ({
      isActive: true,
      hasAcknowledged: false,
      currentStep: 'welcome',

      start: () => {
        set({
          isActive: true,
          currentStep: nextStepMap.welcome
        })
      },

      goToStep: (step) => {
        set({
          isActive: true,
          currentStep: step
        })
      },

      markModelStepDone: () => {
        const { currentStep } = get()
        if (currentStep === 'model') {
          set({
            currentStep: nextStepMap.model
          })
        }
      },

      markPermissionsStepDone: () => {
        const { currentStep } = get()
        if (currentStep === 'permissions') {
          set({
            currentStep: nextStepMap.permissions
          })
        }
      },

      completeAndAcknowledge: () => {
        set({
          isActive: false,
          hasAcknowledged: true,
          currentStep: 'complete'
        })
      },

      skipForNow: () => {
        // Allow users to exit the flow entirely without finishing.
        set({
          isActive: false,
          hasAcknowledged: true,
          currentStep: 'complete'
        })
      },

      reopen: () => {
        set({
          isActive: true
        })
      },

      reset: () => {
        set({
          isActive: true,
          hasAcknowledged: false,
          currentStep: 'welcome'
        })
      },

      checkAndActivateSetup: async () => {
        const { hasAcknowledged, isActive } = get()

        // If setup is already active, don't check again
        if (isActive) {
          console.log('[SetupStore] Setup already active, skipping check')
          return
        }

        try {
          // Check backend configuration status
          const response = await apiClient.checkInitialSetup()

          if (response.success && response.data) {
            const data = response.data as {
              needs_setup?: boolean
              has_models?: boolean
              has_active_model?: boolean
              model_count?: number
            }

            const needsSetup = data.needs_setup ?? false
            const hasModels = data.has_models ?? false

            console.log('[SetupStore] Initial setup check:', {
              needs_setup: needsSetup,
              has_models: hasModels,
              hasAcknowledged,
              isActive
            })

            // If setup is needed, activate the flow (even if hasAcknowledged is true)
            // This handles the case where user deleted config but localStorage still has old state
            if (needsSetup) {
              console.log('[SetupStore] Configuration needed, activating initial setup flow')
              set({
                isActive: true,
                hasAcknowledged: false, // Reset acknowledgment since config is missing
                currentStep: 'welcome'
              })
            } else if (hasModels && !hasAcknowledged) {
              // User has models configured but hasn't acknowledged setup
              // This means they might have configured via settings page
              // Mark as acknowledged to avoid showing welcome screen
              console.log('[SetupStore] User has models, marking setup as acknowledged')
              set({
                hasAcknowledged: true,
                isActive: false
              })
            } else if (hasModels && hasAcknowledged) {
              // Everything is configured and acknowledged - normal state
              console.log('[SetupStore] Setup already completed, no action needed')
            }
          }
        } catch (error) {
          console.error('[SetupStore] Failed to check initial setup:', error)
          // On error, don't force the setup flow - let user access the app
        }
      }
    }),
    {
      name: 'ido-initial-setup',
      partialize: (state) => ({
        isActive: state.isActive,
        hasAcknowledged: state.hasAcknowledged,
        currentStep: state.currentStep
      })
    }
  )
)
