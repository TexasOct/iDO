import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Sparkles, Brain, Shield, CheckCircle2, Loader2, RefreshCw, Plus, Rocket } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PermissionItem } from '@/components/permissions/PermissionItem'

import { useSetupStore, type SetupStep } from '@/lib/stores/setup'
import { useModelsStore } from '@/lib/stores/models'
import { usePermissionsStore } from '@/lib/stores/permissions'
import type { CreateModelInput, LLMModel } from '@/lib/types/models'

const STEP_ORDER: SetupStep[] = ['welcome', 'model', 'permissions', 'complete']

const PROVIDERS = ['openai', 'qwen', 'anthropic', 'cohere', 'together']
const CURRENCIES = ['USD', 'CNY', 'EUR', 'GBP', 'JPY']

const DEFAULT_MODEL_FORM: CreateModelInput = {
  name: '',
  provider: 'openai',
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
                'flex h-10 w-10 items-center justify-center rounded-full border text-sm font-semibold transition-colors',
                isCompleted && 'border-green-500 bg-green-500/10 text-green-200',
                isActive && 'border-primary bg-primary/10 text-primary',
                !isActive && !isCompleted && 'border-muted-foreground/20 text-muted-foreground'
              )}>
              {index + 1}
            </div>
            <div className="mr-4 ml-3">
              <p className="text-foreground text-sm font-medium">{labels[step]}</p>
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

function WelcomeStep({ onStart, onSkip }: { onStart: () => void; onSkip: () => void }) {
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
    <div className="space-y-8">
      <div>
        <Badge variant="secondary" className="gap-2">
          <Sparkles className="h-4 w-4" />
          {t('setup.title')}
        </Badge>
        <h2 className="mt-4 text-3xl font-semibold">{t('setup.welcome.title')}</h2>
        <p className="text-muted-foreground mt-3 text-base">{t('setup.welcome.description')}</p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {highlights.map((highlight, index) => (
          <div key={index} className="bg-muted/40 rounded-xl border p-4">
            <p className="text-foreground text-sm">{highlight}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
        <Button variant="ghost" onClick={onSkip}>
          {t('setup.actions.skip')}
        </Button>
        <Button onClick={onStart} className="gap-2">
          <Sparkles className="h-4 w-4" />
          {t('setup.actions.start')}
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
  testingId
}: {
  models: LLMModel[]
  activeModelId: string | null
  onSelect: (modelId: string) => void
  onTest: (modelId: string) => void
  testingId: string | null
}) {
  const { t } = useTranslation()

  if (!models.length) {
    return (
      <div className="bg-muted/40 flex flex-col items-center justify-center rounded-xl border border-dashed p-6 text-center">
        <Brain className="text-muted-foreground mb-3 h-10 w-10" />
        <p className="text-muted-foreground">{t('setup.model.empty')}</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {models.map((model) => {
        const isActive = !!model.isActive || model.id === activeModelId
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
                <Button size="sm" variant="secondary" onClick={() => onSelect(model.id)}>
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
  const selectModel = useModelsStore((state) => state.selectModel)
  const testModel = useModelsStore((state) => state.testModel)
  const testingModelId = useModelsStore((state) => state.testingModelId)

  const [formData, setFormData] = useState<CreateModelInput>(DEFAULT_MODEL_FORM)
  const [submitting, setSubmitting] = useState(false)

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

  const handleCreateModel = async () => {
    if (!formData.name.trim()) {
      toast.error(t('models.nameRequired'))
      return
    }
    if (!formData.apiKey.trim()) {
      toast.error(t('models.apiKeyRequired'))
      return
    }

    try {
      setSubmitting(true)
      await createModel(formData)
      await fetchModels()
      await fetchActiveModel()
      toast.success(t('models.modelCreatedSuccessfully'))
      setFormData(DEFAULT_MODEL_FORM)
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      toast.error(message || t('models.failedToCreateModel'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleSelectModel = async (modelId: string) => {
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

  return (
    <div className="space-y-6">
      <div>
        <Badge variant="secondary" className="gap-2">
          <Brain className="h-4 w-4" />
          {t('setup.model.title')}
        </Badge>
        <h2 className="mt-4 text-2xl font-semibold">{t('setup.model.heading')}</h2>
        <p className="text-muted-foreground mt-2 text-base">{t('setup.model.description')}</p>
      </div>

      <div className="space-y-4">
        <Label className="text-sm font-semibold">{t('setup.model.formTitle')}</Label>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <Label htmlFor="model-name">{t('setup.model.fields.name')}</Label>
            <Input
              id="model-name"
              value={formData.name}
              onChange={(event) => handleChange('name', event.target.value)}
              placeholder={t('setup.model.placeholders.name')}
            />
          </div>
          <div>
            <Label>{t('setup.model.fields.provider')}</Label>
            <Select value={formData.provider} onValueChange={(value) => handleChange('provider', value)}>
              <SelectTrigger>
                <SelectValue placeholder="OpenAI" />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((provider) => (
                  <SelectItem key={provider} value={provider}>
                    {provider}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="model-model">{t('setup.model.fields.model')}</Label>
            <Input
              id="model-model"
              value={formData.model}
              onChange={(event) => handleChange('model', event.target.value)}
              placeholder="gpt-4o-mini"
            />
          </div>
          <div>
            <Label>{t('setup.model.fields.apiUrl')}</Label>
            <Input
              value={formData.apiUrl}
              onChange={(event) => handleChange('apiUrl', event.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          <div>
            <Label>{t('setup.model.fields.inputPrice')}</Label>
            <Input
              type="number"
              min="0"
              step="0.0001"
              value={formData.inputTokenPrice}
              onChange={(event) => handleChange('inputTokenPrice', event.target.value)}
            />
          </div>
          <div>
            <Label>{t('setup.model.fields.outputPrice')}</Label>
            <Input
              type="number"
              min="0"
              step="0.0001"
              value={formData.outputTokenPrice}
              onChange={(event) => handleChange('outputTokenPrice', event.target.value)}
            />
          </div>
          <div>
            <Label>{t('setup.model.fields.currency')}</Label>
            <Select value={formData.currency} onValueChange={(value) => handleChange('currency', value)}>
              <SelectTrigger>
                <SelectValue placeholder="USD" />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((currency) => (
                  <SelectItem key={currency} value={currency}>
                    {currency}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="model-api-key">{t('setup.model.fields.apiKey')}</Label>
            <Input
              id="model-api-key"
              type="password"
              value={formData.apiKey}
              onChange={(event) => handleChange('apiKey', event.target.value)}
              placeholder="sk-..."
            />
          </div>
        </div>
        <Button onClick={handleCreateModel} disabled={submitting} className="gap-2">
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          {t('setup.model.create')}
        </Button>
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
          testingId={testingModelId}
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
    <div className="space-y-6">
      <div>
        <Badge variant="secondary" className="gap-2">
          <Shield className="h-4 w-4" />
          {t('setup.permissions.title')}
        </Badge>
        <h2 className="mt-4 text-2xl font-semibold">{t('setup.permissions.heading')}</h2>
        <p className="text-muted-foreground mt-2 text-base">{t('setup.permissions.description')}</p>
        {permissionsData?.platform ? (
          <p className="text-muted-foreground mt-1 text-sm">
            {t('setup.permissions.platform', { platform: permissionsData.platform })}
          </p>
        ) : null}
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

function CompletionStep({ onFinish }: { onFinish: () => void }) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6 text-center">
      <div className="bg-primary/10 mx-auto flex h-16 w-16 items-center justify-center rounded-full">
        <Rocket className="text-primary h-8 w-8" />
      </div>
      <h2 className="text-3xl font-semibold">{t('setup.complete.title')}</h2>
      <p className="text-muted-foreground text-base">{t('setup.complete.description')}</p>
      <Button onClick={onFinish} size="lg" className="gap-2">
        <Sparkles className="h-5 w-5" />
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
    <div className="bg-background/90 fixed inset-0 z-50 flex items-center justify-center backdrop-blur">
      <Card className="border-border/40 bg-background/95 mx-4 flex max-h-[90vh] w-full max-w-4xl flex-col gap-6 overflow-y-auto border p-6 shadow-2xl">
        <div className="space-y-2">
          <p className="text-muted-foreground text-sm tracking-widest uppercase">{t('setup.subtitle')}</p>
          <h1 className="text-2xl font-semibold">{t('setup.title')}</h1>
        </div>
        <StepIndicator currentStep={currentStep} labels={stepLabels} />
        <div className="border-t pt-6">{renderStep()}</div>
      </Card>
    </div>
  )
}
