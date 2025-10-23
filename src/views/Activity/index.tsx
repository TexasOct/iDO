import { useEffect, useState, useCallback } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { useActivityIncremental } from '@/hooks/useActivityIncremental'
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll'
import { EmptyState } from '@/components/shared/EmptyState'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { ActivityTimeline } from '@/components/activity/ActivityTimeline'
import { Clock, ExpandIcon, ShrinkIcon, RefreshCw, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { useActivityUpdated, useActivityDeleted, useBulkUpdateCompleted } from '@/hooks/use-tauri-events'

export default function ActivityView() {
  const { t } = useTranslation()
  // 分别订阅各个字段，避免选择器返回新对象
  const timelineData = useActivityStore((state) => state.timelineData)
  const fetchTimelineData = useActivityStore((state) => state.fetchTimelineData)
  const fetchMoreTimelineDataTop = useActivityStore((state) => state.fetchMoreTimelineDataTop)
  const fetchMoreTimelineDataBottom = useActivityStore((state) => state.fetchMoreTimelineDataBottom)
  const loading = useActivityStore((state) => state.loading)
  const loadingMore = useActivityStore((state) => state.loadingMore)
  const hasMoreTop = useActivityStore((state) => state.hasMoreTop)
  const hasMoreBottom = useActivityStore((state) => state.hasMoreBottom)
  const expandAll = useActivityStore((state) => state.expandAll)
  const collapseAll = useActivityStore((state) => state.collapseAll)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [initialized, setInitialized] = useState(false)

  // 处理双向加载
  const handleLoadMore = useCallback(
    async (direction: 'top' | 'bottom') => {
      if (direction === 'top') {
        await fetchMoreTimelineDataTop()
      } else {
        await fetchMoreTimelineDataBottom()
      }
    },
    [fetchMoreTimelineDataTop, fetchMoreTimelineDataBottom]
  )

  // 无限滚动容器
  const { containerRef, sentinelTopRef, sentinelBottomRef } = useInfiniteScroll({
    onLoadMore: handleLoadMore,
    threshold: 300
  })

  // 启用增量更新：订阅后端事件并实时更新时间线
  useActivityIncremental()

  // 刷新时间线数据
  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await fetchTimelineData({ limit: 15 })
    } finally {
      setIsRefreshing(false)
    }
  }

  // 监听后端数据更新事件，自动刷新时间线
  const handleActivityUpdated = useCallback(
    (payload: any) => {
      console.debug('[ActivityView] 收到活动更新事件:', payload.data?.id)
      // 活动被更新时，刷新时间线
      handleRefresh()
    },
    [handleRefresh]
  )

  // 监听活动删除事件
  const handleActivityDeleted = useCallback(
    (payload: any) => {
      console.debug('[ActivityView] 收到活动删除事件:', payload.data?.id)
      // 活动被删除时，刷新时间线
      handleRefresh()
    },
    [handleRefresh]
  )

  // 监听批量更新完成事件
  const handleBulkUpdateCompleted = useCallback(
    (payload: any) => {
      console.debug('[ActivityView] 收到批量更新完成事件，更新数量:', payload.data?.updatedCount)
      // 多个活动被更新时，刷新时间线
      handleRefresh()
    },
    [handleRefresh]
  )

  useActivityUpdated(handleActivityUpdated)
  useActivityDeleted(handleActivityDeleted)
  useBulkUpdateCompleted(handleBulkUpdateCompleted)

  // 仅在组件挂载时初始化加载一次
  useEffect(() => {
    if (!initialized) {
      console.debug('[ActivityView] 首次初始化加载')
      fetchTimelineData({ limit: 15 })
      setInitialized(true)
    }
  }, [initialized, fetchTimelineData])

  if (loading) {
    return <LoadingPage message={t('activity.loadingData')} />
  }

  if (timelineData.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6">
        <EmptyState icon={Clock} title={t('activity.noData')} description={t('activity.noDataDescription')} />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{t('activity.pageTitle')}</h1>
            <p className="text-muted-foreground mt-1 text-sm">{t('activity.description')}</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing || loading}
              className={isRefreshing ? 'animate-spin' : ''}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {isRefreshing ? t('common.loading') : t('common.refresh')}
            </Button>
            <Button variant="outline" size="sm" onClick={expandAll}>
              <ExpandIcon className="mr-2 h-4 w-4" />
              {t('common.expandAll')}
            </Button>
            <Button variant="outline" size="sm" onClick={collapseAll}>
              <ShrinkIcon className="mr-2 h-4 w-4" />
              {t('common.collapseAll')}
            </Button>
          </div>
        </div>
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto p-6">
        {/* 顶部哨兵 - 用于 Intersection Observer */}
        <div ref={sentinelTopRef} className="h-1 bg-transparent" aria-label="Load more top trigger" />

        <ActivityTimeline data={timelineData} />

        {/* 加载更多指示器 */}
        {loadingMore && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="text-muted-foreground h-5 w-5 animate-spin" />
            <span className="text-muted-foreground ml-2 text-sm">{t('common.loading')}</span>
          </div>
        )}

        {/* 没有更多数据提示 */}
        {!hasMoreTop && !hasMoreBottom && timelineData.length > 0 && (
          <div className="flex items-center justify-center py-8">
            <p className="text-muted-foreground text-sm">{t('activity.noMoreData')}</p>
          </div>
        )}

        {/* 底部哨兵 - 用于 Intersection Observer */}
        <div ref={sentinelBottomRef} className="h-1 bg-transparent" aria-label="Load more bottom trigger" />
      </div>
    </div>
  )
}
