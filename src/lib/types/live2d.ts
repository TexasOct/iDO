export type Live2DModelType = 'local' | 'remote'

export interface Live2DModelItem {
  url: string
  type: Live2DModelType
  name?: string
}

export interface Live2DSettings {
  enabled: boolean
  selectedModelUrl: string
  modelDir: string
  remoteModels: string[]
}

export interface Live2DStatePayload {
  settings: Live2DSettings
  models: Live2DModelItem[]
}
