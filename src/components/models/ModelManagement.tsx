import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useModelsStore } from '@/lib/stores/models'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Loader2, Trash2, Plus, Edit } from 'lucide-react'
import type { CreateModelInput, LLMModel } from '@/lib/types/models'

const PROVIDERS = ['openai', 'qwen', 'anthropic', 'cohere', 'together']
const CURRENCIES = ['USD', 'CNY', 'EUR', 'GBP', 'JPY']

export default function ModelManagement() {
  const { t } = useTranslation()
  const models = useModelsStore((state) => state.models)
  const activeModel = useModelsStore((state) => state.activeModel)
  const loading = useModelsStore((state) => state.loading)
  const error = useModelsStore((state) => state.error)
  const fetchModels = useModelsStore((state) => state.fetchModels)
  const fetchActiveModel = useModelsStore((state) => state.fetchActiveModel)
  const createModel = useModelsStore((state) => state.createModel)
  const updateModel = useModelsStore((state) => state.updateModel)
  const selectModel = useModelsStore((state) => state.selectModel)
  const deleteModel = useModelsStore((state) => state.deleteModel)
  const testModel = useModelsStore((state) => state.testModel)
  const setError = useModelsStore((state) => state.setError)
  const testingModelId = useModelsStore((state) => state.testingModelId)

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingModel, setEditingModel] = useState<LLMModel | null>(null)
  const [deleteModelId, setDeleteModelId] = useState<string | null>(null)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [formData, setFormData] = useState<CreateModelInput>({
    name: '',
    provider: 'openai',
    apiUrl: 'https://api.openai.com/v1',
    model: 'gpt-4',
    inputTokenPrice: 0.03,
    outputTokenPrice: 0.06,
    currency: 'USD',
    apiKey: ''
  })

  // Load models on mount
  useEffect(() => {
    fetchModels()
    fetchActiveModel()
  }, [fetchModels, fetchActiveModel])

  // Show error toast if there's an error
  useEffect(() => {
    if (error) {
      toast.error(error)
      setError(null)
    }
  }, [error, setError])

  const handleCreateModel = async () => {
    if (!formData.name.trim()) {
      toast.error(t('models.nameRequired') || 'Model name is required')
      return
    }

    if (!formData.apiKey.trim()) {
      toast.error(t('models.apiKeyRequired') || 'API key is required')
      return
    }

    try {
      await createModel(formData)
      toast.success(t('models.modelCreatedSuccessfully') || 'Model created successfully')
      setIsCreateDialogOpen(false)
      setFormData({
        name: '',
        provider: 'openai',
        apiUrl: 'https://api.openai.com/v1',
        model: 'gpt-4',
        inputTokenPrice: 0.03,
        outputTokenPrice: 0.06,
        currency: 'USD',
        apiKey: ''
      })
    } catch (error) {
      console.error('Failed to create model:', error)
      toast.error(t('models.failedToCreateModel') || 'Failed to create model')
    }
  }

  const handleSelectModel = async (modelId: string) => {
    try {
      await selectModel(modelId)
      toast.success(t('models.modelSelectedSuccessfully') || 'Model selected successfully')
      toast.info(t('models.autoTestingModel') || 'Testing model connection...')
    } catch (error) {
      console.error('Failed to select model:', error)
      toast.error(t('models.failedToSelectModel') || 'Failed to select model')
    }
  }

  const handleDeleteModel = async () => {
    if (!deleteModelId) return

    try {
      await deleteModel(deleteModelId)
      toast.success(t('models.modelDeletedSuccessfully') || 'Model deleted successfully')
      setDeleteModelId(null)
    } catch (error) {
      console.error('Failed to delete model:', error)
      const message = error instanceof Error ? error.message : null
      toast.error(message || t('models.failedToDeleteModel') || 'Failed to delete model')
    }
  }

  const handleTestModel = async (modelId: string) => {
    try {
      const result = await testModel(modelId)
      toast.success(result.message || t('models.testSuccess') || 'Model test passed')
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      toast.error(message || (t('models.testFailed') as string) || 'Model test failed')
    }
  }

  const handleEditModel = (model: LLMModel) => {
    setEditingModel(model)
    setFormData({
      name: model.name,
      provider: model.provider,
      apiUrl: model.apiUrl,
      model: model.model,
      inputTokenPrice: model.inputTokenPrice,
      outputTokenPrice: model.outputTokenPrice,
      currency: model.currency,
      apiKey: '' // 不回显 API Key
    })
    setIsEditDialogOpen(true)
  }

  const handleUpdateModel = async () => {
    if (!editingModel) return

    if (!formData.name.trim()) {
      toast.error(t('models.nameRequired') || 'Model name is required')
      return
    }

    try {
      // Use the proper updateModel API
      await updateModel(editingModel.id, formData)

      toast.success(t('models.modelUpdatedSuccessfully') || 'Model updated successfully')
      setIsEditDialogOpen(false)
      setEditingModel(null)
      setFormData({
        name: '',
        provider: 'openai',
        apiUrl: 'https://api.openai.com/v1',
        model: 'gpt-4',
        inputTokenPrice: 0.03,
        outputTokenPrice: 0.06,
        currency: 'USD',
        apiKey: ''
      })
    } catch (error) {
      console.error('Failed to update model:', error)
      toast.error(t('models.failedToUpdateModel') || 'Failed to update model')
    }
  }

  const formatTimestamp = (value?: string | null) => {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
      return value
    }
    return date.toLocaleString()
  }

  const renderTestStatusMessage = (model: Pick<LLMModel, 'lastTestStatus' | 'lastTestedAt' | 'lastTestError'>) => {
    if (model.lastTestStatus) {
      const time = formatTimestamp(model.lastTestedAt)
      return time
        ? t('models.testStatusPassedDetail', { time }) || `Last tested at ${time}`
        : t('models.testStatusPassed') || 'Test passed'
    }
    if (model.lastTestedAt) {
      const time = formatTimestamp(model.lastTestedAt)
      const reason = model.lastTestError || t('models.testStatusUnknownReason') || 'Unknown error'
      return time
        ? t('models.testStatusFailedDetail', { time, reason }) || `Last failed at ${time}: ${reason}`
        : t('models.testStatusFailed', { reason }) || `Test failed: ${reason}`
    }
    return t('models.testStatusNotTested') || 'Not tested yet'
  }

  const renderTestBadge = (model: Pick<LLMModel, 'lastTestStatus' | 'lastTestedAt'>) => {
    if (model.lastTestStatus) {
      return (
        <Badge variant="outline" className="border-emerald-500 text-emerald-500">
          {t('models.testStatusPassedBadge') || 'Tested'}
        </Badge>
      )
    }
    if (model.lastTestedAt) {
      return (
        <Badge variant="outline" className="border-red-500 text-red-500">
          {t('models.testStatusFailedBadge') || 'Test failed'}
        </Badge>
      )
    }
    return <Badge variant="secondary">{t('models.testStatusPendingBadge') || 'Not tested'}</Badge>
  }

  return (
    <div className="space-y-6">
      {/* Active Model Display */}
      <Card>
        <CardHeader>
          <CardTitle>{t('models.activeModel') || 'Active Model'}</CardTitle>
          <CardDescription>
            {t('models.activeModelDescription') || 'Currently selected model for this application'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {activeModel ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-muted-foreground text-sm font-medium">{t('models.name') || 'Name'}</p>
                  <div className="text-lg font-semibold">{activeModel.name}</div>
                </div>
                <div>
                  <p className="text-muted-foreground text-sm font-medium">{t('models.provider') || 'Provider'}</p>
                  <div className="text-lg font-semibold">
                    <Badge variant="secondary">{activeModel.provider}</Badge>
                  </div>
                </div>
                <div>
                  <p className="text-muted-foreground text-sm font-medium">{t('models.model') || 'Model'}</p>
                  <div className="text-lg font-semibold">{activeModel.model}</div>
                </div>
                <div>
                  <p className="text-muted-foreground text-sm font-medium">{t('models.currency') || 'Currency'}</p>
                  <div className="text-lg font-semibold">{activeModel.currency}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-muted-foreground text-sm font-medium">
                    {t('models.inputTokenPrice') || 'Input Token Price'}
                  </p>
                  <div className="text-sm">
                    {activeModel.inputTokenPrice} {activeModel.currency}/M
                  </div>
                </div>
                <div>
                  <p className="text-muted-foreground text-sm font-medium">
                    {t('models.outputTokenPrice') || 'Output Token Price'}
                  </p>
                  <div className="text-sm">
                    {activeModel.outputTokenPrice} {activeModel.currency}/M
                  </div>
                </div>
              </div>
              <div className="border-border/60 mt-4 rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  {renderTestBadge(activeModel)}
                  <span className="text-sm font-medium">{t('models.testStatusLabel') || 'Test status'}</span>
                </div>
                <p className="text-muted-foreground mt-2 text-sm">{renderTestStatusMessage(activeModel)}</p>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">{t('models.noActiveModel') || 'No active model selected'}</p>
          )}
        </CardContent>
      </Card>

      {/* Model List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>{t('models.allModels') || 'All Models'}</CardTitle>
            <CardDescription>
              {t('models.allModelsDescription') || 'Manage your LLM model configurations'}
            </CardDescription>
          </div>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button disabled={loading}>
                <Plus className="mr-2 h-4 w-4" />
                {t('models.addModel') || 'Add Model'}
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>{t('models.createModel') || 'Create New Model'}</DialogTitle>
                <DialogDescription>
                  {t('models.createModelDescription') || 'Configure a new LLM model for your application'}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                {/* Model Name */}
                <div className="space-y-2">
                  <Label htmlFor="model-name">{t('models.name') || 'Name'}</Label>
                  <Input
                    id="model-name"
                    placeholder={t('models.namePlaceholder') || 'e.g., My GPT-4 Config'}
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                {/* Provider */}
                <div className="space-y-2">
                  <Label htmlFor="provider">{t('models.provider') || 'Provider'}</Label>
                  <Select
                    value={formData.provider}
                    onValueChange={(value) => setFormData({ ...formData, provider: value })}>
                    <SelectTrigger id="provider">
                      <SelectValue />
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

                {/* API URL */}
                <div className="space-y-2">
                  <Label htmlFor="api-url">{t('models.apiUrl') || 'API URL'}</Label>
                  <Input
                    id="api-url"
                    placeholder="https://api.openai.com/v1"
                    value={formData.apiUrl}
                    onChange={(e) => setFormData({ ...formData, apiUrl: e.target.value })}
                  />
                </div>

                {/* Model */}
                <div className="space-y-2">
                  <Label htmlFor="model">{t('models.model') || 'Model'}</Label>
                  <Input
                    id="model"
                    placeholder="gpt-4"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  />
                </div>

                {/* API Key */}
                <div className="space-y-2">
                  <Label htmlFor="api-key">{t('models.apiKey') || 'API Key'}</Label>
                  <Input
                    id="api-key"
                    type="password"
                    placeholder="sk-..."
                    value={formData.apiKey}
                    onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                  />
                </div>

                {/* Input Token Price */}
                <div className="space-y-2">
                  <Label htmlFor="input-price">{t('models.inputTokenPrice') || 'Input Token Price'}</Label>
                  <Input
                    id="input-price"
                    type="number"
                    step="0.0001"
                    min="0"
                    placeholder="0.03"
                    value={formData.inputTokenPrice}
                    onChange={(e) => setFormData({ ...formData, inputTokenPrice: parseFloat(e.target.value) || 0 })}
                  />
                  <p className="text-muted-foreground text-xs">
                    {t('models.pricePerMillion') || 'Price per million tokens'}
                  </p>
                </div>

                {/* Output Token Price */}
                <div className="space-y-2">
                  <Label htmlFor="output-price">{t('models.outputTokenPrice') || 'Output Token Price'}</Label>
                  <Input
                    id="output-price"
                    type="number"
                    step="0.0001"
                    min="0"
                    placeholder="0.06"
                    value={formData.outputTokenPrice}
                    onChange={(e) => setFormData({ ...formData, outputTokenPrice: parseFloat(e.target.value) || 0 })}
                  />
                  <p className="text-muted-foreground text-xs">
                    {t('models.pricePerMillion') || 'Price per million tokens'}
                  </p>
                </div>

                {/* Currency */}
                <div className="space-y-2">
                  <Label htmlFor="currency">{t('models.currency') || 'Currency'}</Label>
                  <Select
                    value={formData.currency}
                    onValueChange={(value) => setFormData({ ...formData, currency: value })}>
                    <SelectTrigger id="currency">
                      <SelectValue />
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

                {/* Create Button */}
                <Button onClick={handleCreateModel} disabled={loading} className="w-full">
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t('models.create') || 'Create'}
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          {/* Edit Model Dialog */}
          <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>{t('models.editModel') || 'Edit Model'}</DialogTitle>
                <DialogDescription>
                  {t('models.editModelDescription') || 'Update your LLM model configuration'}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                {/* Model Name */}
                <div className="space-y-2">
                  <Label htmlFor="edit-model-name">{t('models.name') || 'Name'}</Label>
                  <Input
                    id="edit-model-name"
                    placeholder={t('models.namePlaceholder') || 'e.g., My GPT-4 Config'}
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                {/* Provider */}
                <div className="space-y-2">
                  <Label htmlFor="edit-provider">{t('models.provider') || 'Provider'}</Label>
                  <Select
                    value={formData.provider}
                    onValueChange={(value) => setFormData({ ...formData, provider: value })}>
                    <SelectTrigger id="edit-provider">
                      <SelectValue />
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

                {/* API URL */}
                <div className="space-y-2">
                  <Label htmlFor="edit-api-url">{t('models.apiUrl') || 'API URL'}</Label>
                  <Input
                    id="edit-api-url"
                    placeholder="https://api.openai.com/v1"
                    value={formData.apiUrl}
                    onChange={(e) => setFormData({ ...formData, apiUrl: e.target.value })}
                  />
                </div>

                {/* Model */}
                <div className="space-y-2">
                  <Label htmlFor="edit-model">{t('models.model') || 'Model'}</Label>
                  <Input
                    id="edit-model"
                    placeholder="gpt-4"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  />
                </div>

                {/* API Key */}
                <div className="space-y-2">
                  <Label htmlFor="edit-api-key">{t('models.apiKey') || 'API Key'}</Label>
                  <Input
                    id="edit-api-key"
                    type="password"
                    placeholder={t('models.apiKeyPlaceholder') || 'Leave empty to keep existing key'}
                    value={formData.apiKey}
                    onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                  />
                  <p className="text-muted-foreground text-xs">
                    {t('models.apiKeyEditHint') || 'Leave empty to keep the existing API key'}
                  </p>
                </div>

                {/* Input Token Price */}
                <div className="space-y-2">
                  <Label htmlFor="edit-input-price">{t('models.inputTokenPrice') || 'Input Token Price'}</Label>
                  <Input
                    id="edit-input-price"
                    type="number"
                    step="0.0001"
                    min="0"
                    placeholder="0.03"
                    value={formData.inputTokenPrice}
                    onChange={(e) => setFormData({ ...formData, inputTokenPrice: parseFloat(e.target.value) || 0 })}
                  />
                  <p className="text-muted-foreground text-xs">
                    {t('models.pricePerMillion') || 'Price per million tokens'}
                  </p>
                </div>

                {/* Output Token Price */}
                <div className="space-y-2">
                  <Label htmlFor="edit-output-price">{t('models.outputTokenPrice') || 'Output Token Price'}</Label>
                  <Input
                    id="edit-output-price"
                    type="number"
                    step="0.0001"
                    min="0"
                    placeholder="0.06"
                    value={formData.outputTokenPrice}
                    onChange={(e) => setFormData({ ...formData, outputTokenPrice: parseFloat(e.target.value) || 0 })}
                  />
                  <p className="text-muted-foreground text-xs">
                    {t('models.pricePerMillion') || 'Price per million tokens'}
                  </p>
                </div>

                {/* Currency */}
                <div className="space-y-2">
                  <Label htmlFor="edit-currency">{t('models.currency') || 'Currency'}</Label>
                  <Select
                    value={formData.currency}
                    onValueChange={(value) => setFormData({ ...formData, currency: value })}>
                    <SelectTrigger id="edit-currency">
                      <SelectValue />
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

                {/* Update Button */}
                <Button onClick={handleUpdateModel} disabled={loading} className="w-full">
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t('models.update') || 'Update'}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {loading && models.length === 0 ? (
            <div className="flex justify-center py-8">
              <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
            </div>
          ) : models.length === 0 ? (
            <p className="text-muted-foreground py-8 text-center">
              {t('models.noModels') || 'No models configured yet'}
            </p>
          ) : (
            <div className="space-y-4">
              {models.map((model) => (
                <div
                  key={model.id}
                  className="hover:bg-muted/50 flex items-center justify-between rounded-lg border p-4 transition-colors">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold">{model.name}</h3>
                      <Badge variant="secondary">{model.provider}</Badge>
                      {model.isActive && <Badge variant="default">{t('models.active') || 'Active'}</Badge>}
                      {renderTestBadge(model)}
                    </div>
                    <div className="text-muted-foreground mt-1 text-sm">
                      {model.model} • {model.inputTokenPrice}/{model.outputTokenPrice} {model.currency}/M
                    </div>
                    <div className="text-muted-foreground mt-2 text-xs">{renderTestStatusMessage(model)}</div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestModel(model.id)}
                      disabled={loading || testingModelId === model.id}>
                      {testingModelId === model.id ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          {t('models.testing') || 'Testing...'}
                        </>
                      ) : (
                        t('models.testButton') || 'Test'
                      )}
                    </Button>
                    {!model.isActive && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSelectModel(model.id)}
                        disabled={loading || testingModelId === model.id}>
                        {t('models.select') || 'Select'}
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditModel(model)}
                      disabled={loading || testingModelId === model.id}
                      title={t('models.editButton') || 'Edit'}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Dialog
                      open={isDeleteDialogOpen && deleteModelId === model.id}
                      onOpenChange={(open) => {
                        setIsDeleteDialogOpen(open)
                        if (!open) setDeleteModelId(null)
                      }}>
                      <DialogTrigger asChild>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            setDeleteModelId(model.id)
                            setIsDeleteDialogOpen(true)
                          }}
                          disabled={loading || testingModelId === model.id}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>{t('models.deleteModel') || 'Delete Model'}</DialogTitle>
                          <DialogDescription>
                            {t('models.deleteConfirmation') ||
                              'Are you sure you want to delete this model? This action cannot be undone.'}
                          </DialogDescription>
                        </DialogHeader>
                        <div className="bg-muted rounded-lg p-4">
                          <div className="font-semibold">{model.name}</div>
                          <div className="text-muted-foreground text-sm">{model.provider}</div>
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            onClick={() => {
                              setIsDeleteDialogOpen(false)
                              setDeleteModelId(null)
                            }}>
                            {t('common.cancel') || 'Cancel'}
                          </Button>
                          <Button
                            variant="destructive"
                            onClick={async () => {
                              await handleDeleteModel()
                              setIsDeleteDialogOpen(false)
                              setDeleteModelId(null)
                            }}>
                            {t('common.delete') || 'Delete'}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
