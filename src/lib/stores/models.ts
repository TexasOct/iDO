import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LLMModel, CreateModelInput } from '@/lib/types/models'
import * as apiClient from '@/lib/client/apiClient'

// Type guard for API client - methods are auto-generated and will be available at runtime
const api = apiClient as any

const normalizeModelsResponse = (payload: any): LLMModel[] => {
  if (!payload) return []

  if (Array.isArray(payload)) {
    return payload as LLMModel[]
  }

  if (Array.isArray(payload.models)) {
    return payload.models as LLMModel[]
  }

  if (payload.data) {
    return normalizeModelsResponse(payload.data)
  }

  return []
}

interface ModelsState {
  models: LLMModel[]
  activeModel: LLMModel | null
  loading: boolean
  error: string | null
  selectedModelId: string | null

  // Actions
  fetchModels: () => Promise<void>
  fetchActiveModel: () => Promise<void>
  createModel: (input: CreateModelInput) => Promise<void>
  selectModel: (modelId: string) => Promise<void>
  deleteModel: (modelId: string) => Promise<void>
  setError: (error: string | null) => void
}

export const useModelsStore = create<ModelsState>()(
  persist(
    (set, get) => ({
      models: [],
      activeModel: null,
      loading: false,
      error: null,
      selectedModelId: null,

      fetchModels: async () => {
        set({ loading: true, error: null })
        try {
          const response = await api.listModels(undefined)
          const models = normalizeModelsResponse(response?.data ?? response)

          set({
            models,
            loading: false,
            error: null
          })
        } catch (error) {
          console.error('Failed to fetch models:', error)
          set({ error: (error as Error).message, loading: false })
        }
      },

      fetchActiveModel: async () => {
        set({ loading: true, error: null })
        try {
          const response = await api.getActiveModel(undefined)
          if (response && response.data) {
            const activeModel = response.data as LLMModel
            set({
              activeModel,
              selectedModelId: activeModel?.id || null,
              loading: false,
              error: null
            })
          } else {
            set({ activeModel: null, loading: false, error: null })
          }
        } catch (error) {
          console.error('Failed to fetch active model:', error)
          set({ error: (error as Error).message, loading: false })
        }
      },

      createModel: async (input: CreateModelInput) => {
        set({ loading: true, error: null })
        try {
          const response = await api.createModel({
            name: input.name,
            provider: input.provider,
            apiUrl: input.apiUrl,
            model: input.model,
            inputTokenPrice: input.inputTokenPrice,
            outputTokenPrice: input.outputTokenPrice,
            currency: input.currency,
            apiKey: input.apiKey
          })

          if (response && response.success) {
            // Refresh models list after creation
            await get().fetchModels()
            set({
              loading: false,
              error: null
            })
          } else {
            set({ loading: false })
          }
        } catch (error) {
          console.error('Failed to create model:', error)
          set({ error: (error as Error).message, loading: false })
          throw error
        }
      },

      selectModel: async (modelId: string) => {
        set({ loading: true, error: null })
        try {
          const response = await api.selectModel({
            modelId
          })

          if (response && response.success) {
            // Refresh active model and models list
            const state = get()
            await state.fetchActiveModel()
            await state.fetchModels()
            set({
              selectedModelId: modelId,
              loading: false,
              error: null
            })
          } else {
            set({ loading: false })
          }
        } catch (error) {
          console.error('Failed to select model:', error)
          set({ error: (error as Error).message, loading: false })
          throw error
        }
      },

      deleteModel: async (modelId: string) => {
        set({ loading: true, error: null })
        try {
          const response = await api.deleteModel({
            modelId
          })

          if (response && response.success) {
            // Refresh models list after deletion
            await get().fetchModels()
            set({
              loading: false,
              error: null
            })
          } else {
            set({ loading: false })
          }
        } catch (error) {
          console.error('Failed to delete model:', error)
          set({ error: (error as Error).message, loading: false })
          throw error
        }
      },

      setError: (error: string | null) => {
        set({ error })
      }
    }),
    {
      name: 'rewind-models'
    }
  )
)
