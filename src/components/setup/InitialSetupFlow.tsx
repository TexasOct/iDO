import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { CheckCircle2, Loader2, RefreshCw, Plus, Edit, Trash2, Eye, EyeOff } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PermissionItem } from '@/components/permissions/PermissionItem'

import { useSetupStore, type SetupStep } from '@/lib/stores/setup'
import { useModelsStore } from '@/lib/stores/models'
import { usePermissionsStore } from '@/lib/stores/permissions'
import type { CreateModelInput, LLMModel } from '@/lib/types/models'
import { getMonitors, getScreenSettings, updateScreenSettings, captureAllPreviews } from '@/lib/client/screens'
import type { MonitorInfo, ScreenSetting } from '@/lib/types/settings'
import { ScreenCard } from '@/components/settings/ScreenCard'

const STEP_ORDER: SetupStep[] = ['welcome', 'screens', 'model', 'permissions', 'complete']

const CURRENCIES = ['USD', 'CNY', 'EUR', 'GBP', 'JPY']

const DEFAULT_MODEL_FORM: CreateModelInput = {
  name: '',
  provider: 'openai', // Always 'openai' for OpenAI-compatible APIs
  apiUrl: 'https://api.openai.com/v1',
  model: 'gpt-4o-mini',
  inputTokenPrice: 0.0025,
  outputTokenPrice: 0.01,
  currency: 'USD',
  apiKey: ''
}

/* StepMeta removed — not used anymore */

function StepIndicator({ currentStep, labels }: { currentStep: SetupStep; labels: Record<SetupStep, string> }) {
  const activeIndex = STEP_ORDER.indexOf(currentStep)

  return (
    <div className="flex flex-wrap items-center gap-4">
      {STEP_ORDER.map((step, index) => {
        const isCompleted = index < activeIndex
        const isActive = index === activeIndex

        return (
          <div key={step} className="flex items-center">
            <div
              className={cn(
                'flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors',
                isCompleted && 'border-green-600 bg-green-600 text-white dark:border-green-500 dark:bg-green-500',
                isActive && 'border-primary bg-primary text-primary-foreground',
                !isActive && !isCompleted && 'border-muted-foreground/30 text-muted-foreground'
              )}>
              {index + 1}
            </div>
            <div className="mr-4 ml-3">
              <p
                className={cn(
                  'text-sm font-medium',
                  isActive && 'text-foreground',
                  !isActive && 'text-muted-foreground'
                )}>
                {labels[step]}
              </p>
            </div>
            {index < STEP_ORDER.length - 1 ? (
              <div className="text-muted-foreground bg-muted/80 hidden h-px w-10 shrink-0 sm:block" />
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

function WelcomeStep({ onStart, onSkip }: { onStart: () => void; onSkip: () => Promise<void> }) {
  const { t } = useTranslation()

  const highlights = useMemo(
    () => [
      t('setup.welcome.highlights.local'),
      t('setup.welcome.highlights.ai'),
      t('setup.welcome.highlights.privacy')
    ],
    [t]
  )

  return (
    <div className="mx-auto max-w-2xl space-y-12">
      <div className="space-y-4">
        <h2 className="text-4xl font-bold">{t('setup.welcome.title')}</h2>
        <p className="text-muted-foreground text-lg">{t('setup.welcome.description')}</p>
      </div>

      <div className="space-y-3">
        {highlights.map((highlight, index) => (
          <div key={index} className="flex items-start gap-3">
            <div className="bg-primary/10 text-primary mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold">
              {index + 1}
            </div>
            <p className="text-foreground">{highlight}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={() => void onSkip()} size="lg">
          {t('setup.actions.skip')}
        </Button>
        <Button onClick={onStart} size="lg">
          {t('setup.actions.start')}
        </Button>
      </div>
    </div>
  )
}

function ScreenSetupStep({ onContinue }: { onContinue: () => void }) {
  const { t } = useTranslation()
  const [monitors, setMonitors] = useState<MonitorInfo[]>([])
  const [screenSettings, setScreenSettings] = useState<ScreenSetting[]>([])
  const [monitorPreviews, setMonitorPreviews] = useState<Map<number, string>>(new Map())
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const mergeSettings = useCallback(
    (monitorsList: MonitorInfo[], saved?: ScreenSetting[]) =>
      monitorsList.map((monitor) => {
        const existing = saved?.find((setting) => setting.monitor_index === monitor.index)
        return {
          monitor_index: monitor.index,
          monitor_name: monitor.name,
          is_enabled: existing?.is_enabled ?? monitor.is_primary,
          resolution: monitor.resolution,
          is_primary: monitor.is_primary
        }
      }),
    []
  )

  const persistScreenSettings = useCallback(
    async (settingsToSave: ScreenSetting[], options: { showSuccess?: boolean } = {}) => {
      const { showSuccess = false } = options
      setSaving(true)
      try {
        const response: any = await updateScreenSettings({ screens: settingsToSave as any[] })
        if (!response?.success) {
          throw new Error(response?.message || 'Failed to save screen settings')
        }
        if (showSuccess) {
          toast.success(t('settings.savedSuccessfully'))
        }
      } catch (error) {
        console.error('[ScreenSetupStep] Failed to save screen settings', error)
        toast.error(t('setup.screens.saveFailed'))
      } finally {
        setSaving(false)
      }
    },
    [t]
  )

  const loadScreenInfo = useCallback(async () => {
    setLoading(true)
    try {
      const monitorsResponse: any = await getMonitors()
      const monitorsList =
        monitorsResponse?.success && Array.isArray(monitorsResponse.data?.monitors)
          ? (monitorsResponse.data.monitors as MonitorInfo[])
          : []
      setMonitors(monitorsList)

      let savedSettings: ScreenSetting[] = []
      const settingsResponse: any = await getScreenSettings()
      if (settingsResponse?.success && Array.isArray(settingsResponse.data?.screens)) {
        savedSettings = settingsResponse.data.screens as ScreenSetting[]
      }

      const mergedSettings = mergeSettings(monitorsList, savedSettings)
      setScreenSettings(mergedSettings)

      if (monitorsList.length && !savedSettings.length) {
        await persistScreenSettings(mergedSettings)
      }

      if (monitorsList.length) {
        const previewMap = new Map<number, string>()
        const previewResp: any = await captureAllPreviews()
        if (previewResp?.success && Array.isArray(previewResp.data?.previews)) {
          previewResp.data.previews.forEach((preview: any) => {
            if (preview.image_base64) {
              previewMap.set(preview.monitor_index, preview.image_base64)
            }
          })
        }
        setMonitorPreviews(previewMap)
      } else {
        setMonitorPreviews(new Map())
      }
    } catch (error) {
      console.error('[ScreenSetupStep] Failed to load screen info', error)
      toast.error(t('setup.screens.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [mergeSettings, persistScreenSettings, t])

  useEffect(() => {
    loadScreenInfo().catch((error) => {
      console.error('[ScreenSetupStep] loadScreenInfo failed', error)
    })
  }, [loadScreenInfo])

  const handleScreenToggle = (monitorIndex: number, enabled: boolean) => {
    setScreenSettings((prev) => {
      const updated = mergeSettings(monitors, prev).map((setting) =>
        setting.monitor_index === monitorIndex ? { ...setting, is_enabled: enabled } : setting
      )
      void persistScreenSettings(updated)
      return updated
    })
  }

  const handleResetScreenSettings = async () => {
    if (!monitors.length) return
    const defaults = mergeSettings(monitors)
    setScreenSettings(defaults)
    await persistScreenSettings(defaults, { showSuccess: true })
  }

  const hasSelection = screenSettings.some((setting) => setting.is_enabled)
  const canContinue = hasSelection || monitors.length === 0
  const isBusy = loading || saving

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h2 className="text-3xl font-bold">{t('setup.screens.heading')}</h2>
        <p className="text-muted-foreground text-base">{t('setup.screens.description')}</p>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label>{t('settings.availableScreens')}</Label>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetScreenSettings}
              disabled={monitors.length === 0 || isBusy}>
              {t('settings.resetToDefault')}
            </Button>
            <Button variant="outline" size="sm" onClick={loadScreenInfo} disabled={loading}>
              {loading ? t('common.loading') : t('common.refresh')}
            </Button>
          </div>
        </div>

        {monitors.length === 0 ? (
          <div className="text-muted-foreground flex flex-col gap-2 rounded-lg border border-dashed p-6 text-sm">
            <span>{loading ? t('common.loading') : t('settings.noScreensFound')}</span>
            <span>{t('setup.screens.loadHint')}</span>
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {monitors.map((monitor) => {
              const setting = screenSettings.find((item) => item.monitor_index === monitor.index)
              const preview = monitorPreviews.get(monitor.index)
              const isLoadingPreview = loading && !preview
              return (
                <ScreenCard
                  key={monitor.index}
                  monitor={monitor}
                  setting={setting}
                  preview={preview}
                  onToggle={handleScreenToggle}
                  isLoadingPreview={isLoadingPreview}
                />
              )
            })}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground text-sm">
          {hasSelection
            ? t('setup.screens.continueHint')
            : monitors.length === 0
              ? t('setup.screens.loadHint')
              : t('setup.screens.enableOne')}
        </p>
        <Button onClick={onContinue} disabled={!canContinue || isBusy} className="gap-2">
          {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {t('setup.actions.continue')}
        </Button>
      </div>
    </div>
  )
}

function ModelsList({
  models,
  activeModelId,
  onSelect,
  onTest,
  onEdit,
  onDelete,
  testingId,
  deletingId
}: {
  models: LLMModel[]
  activeModelId: string | null
  onSelect: (modelId: string) => void
  onTest: (modelId: string) => void
  onEdit: (model: LLMModel) => void
  onDelete: (model: LLMModel) => void
  testingId: string | null
  deletingId: string | null
}) {
  const { t } = useTranslation()

  if (!models.length) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-dashed p-8 text-center">
        <p className="text-muted-foreground">{t('setup.model.empty')}</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {models.map((model) => {
        const isActive = !!model.isActive || model.id === activeModelId
        const canSelect = !!model.lastTestStatus
        return (
          <div key={model.id} className="bg-card rounded-xl border p-4 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold">{model.name}</h3>
                <p className="text-muted-foreground text-sm">
                  {model.provider} · {model.model}
                </p>
              </div>
              {isActive ? (
                <Badge variant="outline" className="border-green-500 text-green-400">
                  {t('setup.model.active')}
                </Badge>
              ) : (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onSelect(model.id)}
                  disabled={!canSelect}
                  title={!canSelect ? (t('models.testReminder') as string) : undefined}>
                  {t('setup.model.setActive')}
                </Button>
              )}
            </div>

            <div className="mt-4 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onTest(model.id)}
                disabled={testingId === model.id}
                className="gap-2">
                {testingId === model.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                {t('setup.model.test')}
              </Button>
              <Button size="sm" variant="outline" onClick={() => onEdit(model)} className="gap-2">
                <Edit className="h-4 w-4" />
                {t('models.editButton') || 'Edit'}
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => onDelete(model)}
                disabled={deletingId === model.id}
                className="gap-2">
                {deletingId === model.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                {t('models.deleteModel') || 'Delete model'}
              </Button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ModelSetupStep({ onContinue }: { onContinue: () => void }) {
  const { t } = useTranslation()
  const models = useModelsStore((state) => state.models)
  const activeModel = useModelsStore((state) => state.activeModel)
  const loading = useModelsStore((state) => state.loading)
  const fetchModels = useModelsStore((state) => state.fetchModels)
  const fetchActiveModel = useModelsStore((state) => state.fetchActiveModel)
  const createModel = useModelsStore((state) => state.createModel)
  const updateModel = useModelsStore((state) => state.updateModel)
  const selectModel = useModelsStore((state) => state.selectModel)
  const deleteModel = useModelsStore((state) => state.deleteModel)
  const testModel = useModelsStore((state) => state.testModel)
  const testingModelId = useModelsStore((state) => state.testingModelId)

  const [formData, setFormData] = useState<CreateModelInput>(DEFAULT_MODEL_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [editingModel, setEditingModel] = useState<LLMModel | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [showApiKey, setShowApiKey] = useState(false)

  useEffect(() => {
    if (!models.length) {
      fetchModels().catch(() => {
        // handled by store
      })
    }
    if (!activeModel) {
      fetchActiveModel().catch(() => {
        // handled by store
      })
    }
  }, [models.length, activeModel, fetchModels, fetchActiveModel])

  const hasModel = models.length > 0

  const handleChange = (field: keyof CreateModelInput, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]:
        field === 'inputTokenPrice' || field === 'outputTokenPrice'
          ? Number(value)
          : (value as CreateModelInput[keyof CreateModelInput])
    }))
  }

  const handleSubmitModel = async () => {
    if (!formData.name.trim()) {
      toast.error(t('models.nameRequired'))
      return
    }
    if (!editingModel && !formData.apiKey.trim()) {
      toast.error(t('models.apiKeyRequired'))
      return
    }

    try {
      setSubmitting(true)
      if (editingModel) {
        await updateModel(editingModel.id, {
          ...formData,
          apiKey: formData.apiKey.trim() ? formData.apiKey : undefined
        })
        toast.success(t('models.modelUpdatedSuccessfully'))
        setEditingModel(null)
      } else {
        await createModel(formData)
        toast.success(t('models.modelCreatedSuccessfully'))
      }
      await fetchModels()
      await fetchActiveModel()
      setFormData(DEFAULT_MODEL_FORM)
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      const fallback = editingModel ? t('models.failedToUpdateModel') : t('models.failedToCreateModel')
      toast.error(message || fallback)
    } finally {
      setSubmitting(false)
    }
  }

  const handleSelectModel = async (modelId: string) => {
    const target = models.find((item) => item.id === modelId)
    if (target && !target.lastTestStatus) {
      toast.error(t('models.testReminder'))
      return
    }

    try {
      await selectModel(modelId)
      toast.success(t('models.modelSelectedSuccessfully'))
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      toast.error(message || t('models.failedToSelectModel'))
    }
  }

  const handleTestModel = async (modelId: string) => {
    try {
      const result = await testModel(modelId)
      toast.success(result.message || t('models.testSuccess'))
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      toast.error(message || t('models.testFailed'))
    }
  }

  const handleEditModel = (model: LLMModel) => {
    setEditingModel(model)
    setFormData({
      name: model.name,
      provider: model.provider || 'openai',
      apiUrl: model.apiUrl,
      model: model.model,
      inputTokenPrice: model.inputTokenPrice,
      outputTokenPrice: model.outputTokenPrice,
      currency: model.currency,
      apiKey: ''
    })
  }

  const handleDeleteModel = async (model: LLMModel) => {
    const confirmation = window.confirm(t('models.deleteConfirmation') || 'Are you sure you want to delete this model?')
    if (!confirmation) return

    try {
      setDeletingId(model.id)
      await deleteModel(model.id)
      toast.success(t('models.modelDeletedSuccessfully'))
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      toast.error(message || t('models.failedToDeleteModel'))
    } finally {
      setDeletingId(null)
    }
  }

  const formFields = [
    {
      name: 'name' as const,
      label: t('setup.model.fields.name'),
      type: 'text',
      placeholder: t('setup.model.placeholders.name')
    },
    { name: 'model' as const, label: t('setup.model.fields.model'), type: 'text', placeholder: 'gpt-4o-mini' },
    {
      name: 'apiUrl' as const,
      label: t('setup.model.fields.apiUrl'),
      type: 'text',
      placeholder: 'https://api.openai.com/v1'
    },
    { name: 'inputTokenPrice' as const, label: t('setup.model.fields.inputPrice'), type: 'number', step: '0.0001' },
    { name: 'outputTokenPrice' as const, label: t('setup.model.fields.outputPrice'), type: 'number', step: '0.0001' },
    { name: 'currency' as const, label: t('setup.model.fields.currency'), type: 'select', options: CURRENCIES },
    {
      name: 'apiKey' as const,
      label: t('setup.model.fields.apiKey'),
      type: 'password',
      placeholder: 'sk-...'
    }
  ]

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h2 className="text-3xl font-bold">{t('setup.model.heading')}</h2>
        <p className="text-muted-foreground text-base">{t('setup.model.description')}</p>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">{t('setup.model.formTitle')}</h3>
        <div className="grid gap-4 md:grid-cols-2">
          {/* API Type - Static Display */}
          <div className="space-y-2">
            <Label>{t('models.apiType') || 'API Type'}</Label>
            <div className="border-input bg-muted flex h-10 w-full items-center rounded-md border px-3 py-2 text-sm">
              OpenAI-Compatible API
            </div>
          </div>

          {formFields.map((field) => {
            const isApiKey = field.name === 'apiKey'
            const inputType = isApiKey ? (showApiKey ? 'text' : 'password') : field.type
            return (
              <div key={field.name} className="space-y-2">
                <Label htmlFor={`model-${field.name}`}>{field.label}</Label>
                {field.type === 'select' ? (
                  <Select
                    value={String(formData[field.name])}
                    onValueChange={(value) => handleChange(field.name, value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {field.options?.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="relative">
                    <Input
                      id={`model-${field.name}`}
                      type={inputType}
                      value={String(formData[field.name])}
                      onChange={(event) => handleChange(field.name, event.target.value)}
                      placeholder={field.placeholder}
                      className={cn('placeholder:text-muted-foreground/50', isApiKey && 'pr-10')}
                      {...(field.type === 'number' && { min: '0', step: field.step })}
                    />
                    {isApiKey ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="text-muted-foreground absolute top-1.5 right-1.5 h-7 w-7"
                        onClick={() => setShowApiKey((prev) => !prev)}>
                        {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        <span className="sr-only">{showApiKey ? 'Hide API key' : 'Show API key'}</span>
                      </Button>
                    ) : null}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={handleSubmitModel} disabled={submitting} className="gap-2">
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : editingModel ? (
              <Edit className="h-4 w-4" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            {editingModel ? t('models.update') || 'Update' : t('setup.model.create')}
          </Button>
          {editingModel ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setEditingModel(null)
                setFormData(DEFAULT_MODEL_FORM)
              }}>
              {t('common.cancel') || 'Cancel'}
            </Button>
          ) : null}
        </div>
        {editingModel ? (
          <p className="text-muted-foreground text-xs">
            {t('models.apiKeyEditHint') || 'Leave empty to keep existing API key'}
          </p>
        ) : null}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">{t('setup.model.listTitle')}</h3>
          <Button variant="ghost" size="sm" onClick={() => fetchModels()} disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>
        <ModelsList
          models={models}
          activeModelId={activeModel?.id ?? null}
          onSelect={handleSelectModel}
          onTest={handleTestModel}
          onEdit={handleEditModel}
          onDelete={handleDeleteModel}
          testingId={testingModelId}
          deletingId={deletingId}
        />
      </div>

      <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground text-sm">{t('setup.model.continueHint')}</p>
        <Button onClick={onContinue} disabled={!hasModel}>
          {t('setup.actions.continue')}
        </Button>
      </div>
    </div>
  )
}

function PermissionsSetupStep({ onContinue }: { onContinue: () => void }) {
  const { t } = useTranslation()

  const permissionsData = usePermissionsStore((state) => state.permissionsData)
  const loading = usePermissionsStore((state) => state.loading)
  const checkPermissions = usePermissionsStore((state) => state.checkPermissions)
  const openSystemSettings = usePermissionsStore((state) => state.openSystemSettings)
  const requestAccessibility = usePermissionsStore((state) => state.requestAccessibility)
  const restartApp = usePermissionsStore((state) => state.restartApp)

  useEffect(() => {
    if (!permissionsData) {
      checkPermissions().catch(() => {
        // handled by store
      })
    }
  }, [permissionsData, checkPermissions])

  useEffect(() => {
    if (permissionsData?.allGranted) {
      // Give the UI time to show the success state before auto-advancing.
      const timeout = setTimeout(() => {
        onContinue()
      }, 800)
      return () => clearTimeout(timeout)
    }
  }, [permissionsData?.allGranted, onContinue])

  const handleRecheck = async () => {
    try {
      await checkPermissions()
      toast.success(t('settings.permissionCheckSuccess'))
    } catch (error) {
      toast.error(t('settings.permissionCheckFailed'))
    }
  }

  const handleOpenSettings = async (permissionType: string) => {
    try {
      await openSystemSettings(permissionType)
      toast.success(t('permissions.settingsOpened'))
    } catch (error) {
      toast.error(t('permissions.openSettingsFailed'))
    }
  }

  const handleRequestAccessibility = async () => {
    try {
      await requestAccessibility()
      // Use a simple informational message here (avoid referencing a missing i18n key)
      toast.info('Accessibility permission requested')
    } catch (error) {
      toast.error(t('permissions.openSettingsFailed'))
    }
  }

  const handleRestart = async () => {
    try {
      toast.info(t('permissions.restarting'))
      await restartApp()
    } catch (error) {
      toast.error(t('permissions.restartFailed'))
    }
  }

  const allGranted = permissionsData?.allGranted

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h2 className="text-3xl font-bold">{t('setup.permissions.heading')}</h2>
        <p className="text-muted-foreground text-base">{t('setup.permissions.description')}</p>
      </div>

      {permissionsData ? (
        <div className="space-y-4">
          <div
            className={cn(
              'rounded-lg border p-4',
              allGranted ? 'border-green-500/50 bg-green-500/10' : 'border-yellow-500/40 bg-yellow-500/5'
            )}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle2 className={cn('h-5 w-5', allGranted ? 'text-green-400' : 'text-yellow-400')} />
                <span className="text-sm font-medium">
                  {allGranted ? t('setup.permissions.allGranted') : t('setup.permissions.pending')}
                </span>
              </div>
              <Button variant="outline" size="sm" onClick={handleRecheck} disabled={loading} className="gap-2">
                <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
                {t('setup.permissions.recheck')}
              </Button>
            </div>
            {permissionsData.needsRestart ? (
              <p className="text-muted-foreground mt-2 text-sm">{t('setup.permissions.restartHint')}</p>
            ) : (
              <p className="text-muted-foreground mt-2 text-sm">{t('setup.permissions.instructions')}</p>
            )}
          </div>

          <div className="space-y-3">
            {Object.values(permissionsData.permissions).map((permission) => (
              <PermissionItem key={permission.type} permission={permission} onOpenSettings={handleOpenSettings} />
            ))}
          </div>

          <div className="flex flex-wrap gap-3">
            <Button variant="outline" onClick={handleRequestAccessibility}>
              {t('setup.permissions.requestAccessibility')}
            </Button>
            {permissionsData.needsRestart ? (
              <Button onClick={handleRestart} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                {t('permissions.guide.restartApp')}
              </Button>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed p-10 text-center">
          <Loader2 className="text-muted-foreground mb-3 h-8 w-8 animate-spin" />
          <p className="text-muted-foreground">{t('settings.permissionChecking')}</p>
        </div>
      )}

      <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground text-sm">
          {allGranted ? 'Will advance automatically' : 'Waiting for required permissions'}
        </p>
        <Button onClick={onContinue} disabled={!allGranted}>
          {t('setup.actions.continue')}
        </Button>
      </div>
    </div>
  )
}

function CompletionStep({ onFinish }: { onFinish: () => Promise<void> }) {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-xl space-y-8 text-center">
      <div className="space-y-4">
        <h2 className="text-4xl font-bold">{t('setup.complete.title')}</h2>
        <p className="text-muted-foreground text-lg">{t('setup.complete.description')}</p>
      </div>
      <Button onClick={() => void onFinish()} size="lg">
        {t('setup.complete.action')}
      </Button>
    </div>
  )
}

export function InitialSetupFlow() {
  const { t } = useTranslation()

  const isActive = useSetupStore((state) => state.isActive)
  const hasAcknowledged = useSetupStore((state) => state.hasAcknowledged)
  const currentStep = useSetupStore((state) => state.currentStep)
  const start = useSetupStore((state) => state.start)
  const markScreensStepDone = useSetupStore((state) => state.markScreensStepDone)
  const markModelStepDone = useSetupStore((state) => state.markModelStepDone)
  const markPermissionsStepDone = useSetupStore((state) => state.markPermissionsStepDone)
  const completeAndAcknowledge = useSetupStore((state) => state.completeAndAcknowledge)
  const skipForNow = useSetupStore((state) => state.skipForNow)

  const permissionsData = usePermissionsStore((state) => state.permissionsData)
  const pendingRestart = usePermissionsStore((state) => state.pendingRestart)

  // Auto-advance from the permissions step when appropriate.
  // - If permissions are all granted and a restart is not required, advance immediately.
  // - If a restart was required and we previously triggered a restart (pendingRestart === true),
  //   wait until pendingRestart has been cleared (which indicates the restart flow completed
  //   and the app/state has been refreshed). After that, if permissions are still all granted,
  //   advance the setup flow.
  useEffect(() => {
    if (currentStep !== 'permissions') return

    const allGranted = permissionsData?.allGranted
    const needsRestart = permissionsData?.needsRestart

    if (allGranted) {
      // If a restart was required and we have a pending restart flag, wait until it's cleared.
      if (needsRestart && pendingRestart) {
        return
      }

      markPermissionsStepDone()
    }
  }, [currentStep, permissionsData?.allGranted, permissionsData?.needsRestart, pendingRestart, markPermissionsStepDone])

  const shouldShow = isActive && !hasAcknowledged

  const stepLabels: Record<SetupStep, string> = useMemo(
    () => ({
      welcome: t('setup.steps.welcome'),
      screens: t('setup.steps.screens'),
      model: t('setup.steps.model'),
      permissions: t('setup.steps.permissions'),
      complete: t('setup.steps.complete')
    }),
    [t]
  )

  const renderStep = () => {
    switch (currentStep) {
      case 'welcome':
        return <WelcomeStep onStart={start} onSkip={skipForNow} />
      case 'screens':
        return <ScreenSetupStep onContinue={markScreensStepDone} />
      case 'model':
        return <ModelSetupStep onContinue={markModelStepDone} />
      case 'permissions':
        return <PermissionsSetupStep onContinue={markPermissionsStepDone} />
      case 'complete':
        return <CompletionStep onFinish={completeAndAcknowledge} />
      default:
        return null
    }
  }

  if (!shouldShow) {
    return null
  }

  return (
    <div className="bg-background fixed inset-0 z-50 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b px-8 py-5">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-2xl font-bold">{t('setup.title')}</h1>
        </div>
      </div>

      {/* Step Indicator */}
      <div className="px-8 py-6">
        <div className="mx-auto max-w-3xl">
          <StepIndicator currentStep={currentStep} labels={stepLabels} />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-8 py-8">
        <div className="mx-auto max-w-3xl">{renderStep()}</div>
      </div>
    </div>
  )
}
