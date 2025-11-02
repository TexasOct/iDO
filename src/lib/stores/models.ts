import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { pyInvoke } from 'tauri-plugin-pytauri-api'
import type { LLMModel, CreateModelInput } from '@/lib/types/models'
import * as apiClient from '@/lib/client/apiClient'

// Type guard for API client - methods are auto-generated and will be available at runtime
const api = apiClient as any

const normalizeModelsResponse = (payload: any): any[] => {
  if (!payload) return []

  if (Array.isArray(payload)) {
    return payload
  }

  if (Array.isArray(payload.models)) {
    return payload.models
  }

  if (payload.data) {
    return normalizeModelsResponse(payload.data)
  }

  return []
}

const transformModel = (model: any): LLMModel => ({
  id: model?.id ?? '',
  name: model?.name ?? '',
  provider: model?.provider ?? '',
  apiUrl: model?.apiUrl ?? model?.api_url ?? '',
  model: model?.model ?? '',
  inputTokenPrice: Number(model?.inputTokenPrice ?? model?.input_token_price ?? 0),
  outputTokenPrice: Number(model?.outputTokenPrice ?? model?.output_token_price ?? 0),
  currency: model?.currency ?? 'USD',
  isActive: Boolean(model?.isActive ?? model?.is_active ?? false),
  lastTestStatus:
    typeof model?.lastTestStatus === 'boolean'
      ? model.lastTestStatus
      : Boolean(model?.lastTestStatus ?? model?.last_test_status ?? false),
  lastTestedAt: model?.lastTestedAt ?? model?.last_tested_at ?? null,
  lastTestError: model?.lastTestError ?? model?.last_test_error ?? null,
  createdAt: model?.createdAt ?? model?.created_at ?? '',
  updatedAt: model?.updatedAt ?? model?.updated_at ?? ''
})

interface ModelsState {
  models: LLMModel[]
  activeModel: LLMModel | null
  loading: boolean
  error: string | null
  selectedModelId: string | null
  testingModelId: string | null

  // Actions
  fetchModels: () => Promise<void>
  fetchActiveModel: () => Promise<void>
  createModel: (input: CreateModelInput) => Promise<void>
  updateModel: (modelId: string, input: Partial<CreateModelInput>) => Promise<void>
  selectModel: (modelId: string) => Promise<void>
  deleteModel: (modelId: string) => Promise<void>
  testModel: (modelId: string) => Promise<{ success: boolean; message?: string | null }>
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
      testingModelId: null,

      fetchModels: async () => {
        set({ loading: true, error: null })
        try {
          const response = await api.listModels(undefined)
          const models = normalizeModelsResponse(response?.data ?? response).map(transformModel)

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
            const activeModel = transformModel(response.data)
            set({
              activeModel,
              selectedModelId: activeModel?.id || null,
              loading: false,
              error: null
            })
          } else {
            set({
              activeModel: null,
              selectedModelId: null,
              loading: false,
              error: null
            })
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

      updateModel: async (modelId: string, input: Partial<CreateModelInput>) => {
        set({ loading: true, error: null })
        try {
          const response = await api.updateModel({
            modelId,
            name: input.name,
            provider: input.provider,
            apiUrl: input.apiUrl,
            model: input.model,
            inputTokenPrice: input.inputTokenPrice,
            outputTokenPrice: input.outputTokenPrice,
            currency: input.currency,
            apiKey: input.apiKey || undefined // 空字符串转为 undefined，保持现有密钥
          })

          if (response && response.success) {
            // Refresh models list after update
            await get().fetchModels()
            await get().fetchActiveModel()
            set({
              loading: false,
              error: null
            })
          } else {
            set({ loading: false })
          }
        } catch (error) {
          console.error('Failed to update model:', error)
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

            // 自动测试新选中的模型
            console.debug('[ModelsStore] 模型已选中，开始自动测试:', modelId)
            try {
              await state.testModel(modelId)
              console.debug('[ModelsStore] 模型自动测试成功')
            } catch (testError) {
              console.warn('[ModelsStore] 模型自动测试失败:', testError)
              // 测试失败不影响选择操作，仅记录警告
            }
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

          if (!response?.success) {
            const message = response?.message || 'Failed to delete model'
            set({ loading: false, error: message })
            throw new Error(message)
          }

          const state = get()
          await Promise.all([state.fetchModels(), state.fetchActiveModel()])
        } catch (error) {
          console.error('Failed to delete model:', error)
          const message = error instanceof Error ? error.message : String(error)
          set({ error: message, loading: false })
          throw error
        }
      },

      testModel: async (modelId: string) => {
        set({ testingModelId: modelId })
        try {
          const response = (await pyInvoke('test_model', { modelId })) as {
            success?: boolean
            message?: string
          }

          const state = get()
          await Promise.all([state.fetchModels(), state.fetchActiveModel()])
          set({ testingModelId: null })

          if (!response?.success) {
            throw new Error(response?.message || '模型测试失败')
          }

          return {
            success: true,
            message: response.message
          }
        } catch (error) {
          set({ testingModelId: null })
          throw error
        }
      },

      setError: (error: string | null) => {
        set({ error })
      }
    }),
    {
      name: 'rewind-models',
      partialize: (state) => ({
        models: state.models,
        activeModel: state.activeModel,
        selectedModelId: state.selectedModelId
      })
    }
  )
)
