import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { getPersistenceStats, cleanupOrphanedImages } from '@/lib/client/apiClient'
import { RefreshCw, Database, HardDrive, FileText, Image as ImageIcon, Trash2 } from 'lucide-react'

interface PersistenceStats {
  databasePath?: string
  databaseSize?: number
  screenshotPath?: string
  screenshotSize?: number
  activities?: number
  events?: number
  tasks?: number
  llmModels?: number
  llmTokenUsage?: number
  settings?: number
  rawRecords?: number
  knowledge?: number
  todos?: number
  diaries?: number
}

interface StorageSettingsProps {
  className?: string
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

const formatNumber = (num: number): string => {
  return num.toLocaleString()
}

export function StorageSettings({ className }: StorageSettingsProps) {
  const { t } = useTranslation()
  const [stats, setStats] = useState<PersistenceStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [cleaning, setCleaning] = useState(false)

  const fetchStats = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }

      const response = await getPersistenceStats()

      if (response && typeof response === 'object' && 'data' in response) {
        const data = response.data as PersistenceStats
        setStats(data)

        if (isRefresh) {
          toast.success(t('settings.storage.statsRefreshed'))
        }
      }
    } catch (error) {
      console.error('Failed to fetch persistence stats:', error)
      toast.error(t('settings.storage.statsLoadFailed'))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void fetchStats()
  }, [])

  const handleCleanupOrphanedImages = async () => {
    try {
      setCleaning(true)
      const response = await cleanupOrphanedImages()

      if (response && typeof response === 'object' && 'success' in response) {
        if (response.success) {
          const data = response.data as { cleanedCount?: number }
          const count = data?.cleanedCount || 0
          toast.success(t('settings.storage.cleanupSuccess', { count }))
          // Refresh stats after cleanup
          await fetchStats(true)
        } else {
          toast.error(t('settings.storage.cleanupFailed'))
        }
      }
    } catch (error) {
      console.error('Failed to cleanup orphaned images:', error)
      toast.error(t('settings.storage.cleanupFailed'))
    } finally {
      setCleaning(false)
    }
  }

  const databaseSize = stats?.databaseSize || 0
  const screenshotSize = stats?.screenshotSize || 0
  const totalSize = databaseSize + screenshotSize
  const maxRecommendedSize = 1024 * 1024 * 1024 * 5 // 5GB total recommended
  const totalUsagePercentage = Math.min((totalSize / maxRecommendedSize) * 100, 100)
  const databasePercentage = totalSize > 0 ? (databaseSize / totalSize) * 100 : 0
  const screenshotPercentage = totalSize > 0 ? (screenshotSize / totalSize) * 100 : 0

  const dataStats = [
    {
      label: t('settings.storage.activities'),
      count: stats?.activities || 0,
      icon: FileText,
      color: 'text-chart-1'
    },
    {
      label: t('settings.storage.events'),
      count: stats?.events || 0,
      icon: FileText,
      color: 'text-chart-2'
    },
    {
      label: t('settings.storage.knowledge'),
      count: stats?.knowledge || 0,
      icon: FileText,
      color: 'text-chart-3'
    },
    {
      label: t('settings.storage.todos'),
      count: stats?.todos || 0,
      icon: FileText,
      color: 'text-chart-4'
    },
    {
      label: t('settings.storage.diaries'),
      count: stats?.diaries || 0,
      icon: FileText,
      color: 'text-chart-5'
    },
    {
      label: t('settings.storage.rawRecords'),
      count: stats?.rawRecords || 0,
      icon: Database,
      color: 'text-muted-foreground'
    }
  ]

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{t('settings.storage.title')}</CardTitle>
          <CardDescription>{t('settings.storage.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="text-muted-foreground h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{t('settings.storage.title')}</CardTitle>
            <CardDescription>{t('settings.storage.description')}</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => fetchStats(true)} disabled={refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Total Storage Overview */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HardDrive className="text-primary h-5 w-5" />
              <span className="font-medium">{t('settings.storage.totalSize')}</span>
            </div>
            <span className="text-foreground text-2xl font-bold">{formatBytes(totalSize)}</span>
          </div>

          {/* Stacked Progress Bar */}
          <div className="space-y-2">
            <div className="bg-secondary relative h-3 w-full overflow-hidden rounded-full">
              {/* Database portion - Blue */}
              <div
                className="bg-chart-1 absolute top-0 left-0 h-full transition-all duration-300 ease-in-out"
                style={{ width: `${(databaseSize / maxRecommendedSize) * 100}%` }}
              />
              {/* Screenshot portion - Orange, starts after database */}
              <div
                className="bg-chart-2 absolute top-0 h-full transition-all duration-300 ease-in-out"
                style={{
                  left: `${(databaseSize / maxRecommendedSize) * 100}%`,
                  width: `${(screenshotSize / maxRecommendedSize) * 100}%`
                }}
              />
            </div>
            <div className="text-muted-foreground flex justify-between text-xs">
              <span>{t('settings.storage.currentUsage')}</span>
              <span>
                {t('settings.storage.recommended')}: {formatBytes(maxRecommendedSize)}
              </span>
            </div>
          </div>

          {totalUsagePercentage > 80 && (
            <div className="bg-destructive/10 border-destructive/20 text-destructive rounded-md border p-3 text-sm">
              {t('settings.storage.highUsageWarning')}
            </div>
          )}
        </div>

        {/* Storage Breakdown with Cleanup Button */}
        <div className="grid gap-3 sm:grid-cols-2">
          {/* Database */}
          <div className="bg-muted/50 rounded-lg p-4">
            <div className="mb-2 flex items-center gap-2">
              <div className="bg-chart-1 h-3 w-3 rounded-full" />
              <span className="text-sm font-medium">{t('settings.storage.database')}</span>
            </div>
            <div className="text-foreground text-xl font-bold">{formatBytes(databaseSize)}</div>
            <div className="text-muted-foreground mt-1 text-xs">
              {databasePercentage.toFixed(1)}% {t('settings.storage.ofTotal')}
            </div>
          </div>

          {/* Screenshots with Cleanup Button */}
          <div className="bg-muted/50 rounded-lg p-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="bg-chart-2 h-3 w-3 rounded-full" />
                <span className="text-sm font-medium">{t('settings.storage.screenshots')}</span>
              </div>
            </div>
            <div className="text-foreground text-xl font-bold">{formatBytes(screenshotSize)}</div>
            <div className="text-muted-foreground mt-1 text-xs">
              {screenshotPercentage.toFixed(1)}% {t('settings.storage.ofTotal')}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCleanupOrphanedImages}
              disabled={cleaning}
              className="mt-3 w-full">
              <Trash2 className={`mr-2 h-3 w-3 ${cleaning ? 'animate-pulse' : ''}`} />
              {cleaning ? t('settings.storage.cleaning') : t('settings.storage.cleanupOrphaned')}
            </Button>
          </div>
        </div>

        {/* Storage Paths */}
        {(stats?.databasePath || stats?.screenshotPath) && (
          <div className="space-y-2">
            {stats?.databasePath && (
              <div className="bg-muted rounded-md p-3">
                <div className="text-muted-foreground mb-1 flex items-center gap-2 text-xs">
                  <Database className="h-3 w-3" />
                  {t('settings.storage.databasePath')}
                </div>
                <div className="font-mono text-xs break-all">{stats.databasePath}</div>
              </div>
            )}
            {stats?.screenshotPath && (
              <div className="bg-muted rounded-md p-3">
                <div className="text-muted-foreground mb-1 flex items-center gap-2 text-xs">
                  <ImageIcon className="h-3 w-3" />
                  {t('settings.storage.screenshotPath')}
                </div>
                <div className="font-mono text-xs break-all">{stats.screenshotPath}</div>
              </div>
            )}
          </div>
        )}

        {/* Data Statistics */}
        <div className="space-y-3">
          <div className="border-border border-t pt-4">
            <h4 className="mb-3 font-medium">{t('settings.storage.dataBreakdown')}</h4>
            <div className="grid gap-3">
              {dataStats.map((stat) => {
                const Icon = stat.icon
                return (
                  <div key={stat.label} className="bg-muted/50 flex items-center justify-between rounded-lg p-3">
                    <div className="flex items-center gap-3">
                      <Icon className={`h-4 w-4 ${stat.color}`} />
                      <span className="text-sm">{stat.label}</span>
                    </div>
                    <span className="font-mono text-sm font-medium">{formatNumber(stat.count)}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Tips */}
        <div className="bg-muted/50 rounded-md p-4">
          <p className="text-muted-foreground text-sm">💡 {t('settings.storage.tip')}</p>
        </div>
      </CardContent>
    </Card>
  )
}
