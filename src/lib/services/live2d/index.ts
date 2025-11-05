import type { Live2DModelItem, Live2DSettings, Live2DStatePayload } from '@/lib/types/live2d'
import * as apiClient from '@/lib/client/apiClient'

export const DEFAULT_MODEL_URL =
  'https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/shizuku/shizuku.model.json'

const normalizeRemoteList = (raw: unknown): string[] => {
  if (!Array.isArray(raw)) return [DEFAULT_MODEL_URL]
  const list = raw
    .map((item) => (typeof item === 'string' ? item.trim() : String(item || '').trim()))
    .filter((item) => item.length > 0)
  return list.length > 0 ? Array.from(new Set(list)) : [DEFAULT_MODEL_URL]
}

const normalizeSettings = (raw: any): Live2DSettings => {
  const remoteModels = normalizeRemoteList(raw?.remoteModels ?? raw?.remote_models)
  const selected =
    (raw?.selectedModelUrl as string | undefined) ??
    (raw?.selected_model_url as string | undefined) ??
    remoteModels[0] ??
    DEFAULT_MODEL_URL

  return {
    enabled: Boolean(raw?.enabled),
    selectedModelUrl: selected,
    modelDir: typeof raw?.modelDir === 'string' ? raw.modelDir : typeof raw?.model_dir === 'string' ? raw.model_dir : '',
    remoteModels
  }
}

const normalizeModels = (raw: any): Live2DModelItem[] => {
  const normalizeArray = (items: any, type: Live2DModelItem['type']): Live2DModelItem[] =>
    Array.isArray(items)
      ? items
          .map((item) => {
            const url = typeof item?.url === 'string' ? item.url : String(item?.url || '').trim()
            if (!url) return null
            const name =
              typeof item?.name === 'string'
                ? item.name
                : url.split('/').filter(Boolean).slice(-1)[0] || (type === 'local' ? 'Local Model' : 'Remote Model')
            return { url, type, name }
          })
          .filter(Boolean) as Live2DModelItem[]
      : []

  const localModels = normalizeArray(raw?.local, 'local')
  const remoteModels = normalizeArray(raw?.remote, 'remote')

  const combinedMap = new Map<string, Live2DModelItem>()
  ;[...localModels, ...remoteModels].forEach((item) => {
    combinedMap.set(item.url, item)
  })

  return Array.from(combinedMap.values())
}

const mapResponseToState = (payload: any): Live2DStatePayload => {
  const settings = normalizeSettings(payload?.settings ?? {})
  const models = normalizeModels(payload?.models ?? {})
  return { settings, models }
}

export async function fetchLive2dState(): Promise<Live2DStatePayload> {
  const response = await apiClient.getLive2dSettings(undefined)
  return mapResponseToState(response?.data)
}

export async function updateLive2dState(
  updates: Partial<Pick<Live2DSettings, 'enabled' | 'modelDir' | 'remoteModels' | 'selectedModelUrl'>>
): Promise<Live2DStatePayload> {
  const payload: Record<string, unknown> = {}
  if (typeof updates.enabled !== 'undefined') payload.enabled = updates.enabled
  if (typeof updates.modelDir !== 'undefined') payload.modelDir = updates.modelDir
  if (typeof updates.remoteModels !== 'undefined') payload.remoteModels = updates.remoteModels
  if (typeof updates.selectedModelUrl !== 'undefined') payload.selectedModelUrl = updates.selectedModelUrl

  const response = await apiClient.updateLive2dSettings(payload as any)
  return mapResponseToState(response?.data)
}
