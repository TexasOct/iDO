import { create } from 'zustand'
import { persist } from 'zustand/middleware'

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
