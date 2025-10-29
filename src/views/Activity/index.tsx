import { useEffect, useState, useCallback, useRef } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { useActivitySync } from '@/hooks/useActivitySync'
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll'
import { EmptyState } from '@/components/shared/EmptyState'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { ActivityTimeline } from '@/components/activity/ActivityTimeline'
import { Clock, RefreshCw, Loader2 } from 'lucide-react'
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
  const isAtLatest = useActivityStore((state) => state.isAtLatest)
  const setIsAtLatest = useActivityStore((state) => state.setIsAtLatest)
  const fetchActivityCountByDate = useActivityStore((state) => state.fetchActivityCountByDate)
  const applyActivityUpdate = useActivityStore((state) => state.applyActivityUpdate)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [initialized, setInitialized] = useState(false)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const eventDebounceRef = useRef<{ timer: NodeJS.Timeout | null; lastEventTime: number }>({
    timer: null,
    lastEventTime: 0
  })

  // 监听滚动位置，更新 isAtLatest 状态
  // 滑动窗口策略：当滚动窗口接近顶部时，允许接收实时推送
  useEffect(() => {
    const handleScroll = () => {
      const container = scrollContainerRef.current
      if (!container) return

      // 滑动窗口策略：
      // - 如果在顶部 50px 以内，认为在最新位置，接收实时推送
      // - 这样既能保证实时性，又不会在用户向下滚动一点点时就停止更新
      const isAtTop = container.scrollTop <= 50
      setIsAtLatest(isAtTop)

      // 调试日志
      if (isAtTop !== useActivityStore.getState().isAtLatest) {
        console.debug('[ActivityView] isAtLatest 状态变化:', {
          scrollTop: container.scrollTop,
          isAtTop
        })
      }
    }

    const container = scrollContainerRef.current
    if (!container) return

    container.addEventListener('scroll', handleScroll)

    // 立即执行一次，确保初始状态正确
    handleScroll()

    return () => container.removeEventListener('scroll', handleScroll)
  }, [setIsAtLatest])

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

  // 调试：监听 hasMore 状态变化
  useEffect(() => {
    console.log('[ActivityView] hasMore 状态:', {
      hasMoreTop,
      hasMoreBottom,
      loadingMore,
      timelineDataLength: timelineData.length
    })
  }, [hasMoreTop, hasMoreBottom, loadingMore, timelineData.length])

  // 启用活动同步：集成增量更新、错误恢复、备用策略等功能
  useActivitySync()

  // 刷新时间线数据
  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await fetchTimelineData({ limit: 15 })
    } finally {
      setIsRefreshing(false)
    }
  }

  const setTimelineData = useActivityStore((state) => state.setTimelineData)

  // 去抖处理函数工厂：避免短时间内频繁的事件处理
  // 使用积累模式：在延迟期间的多个事件会被合并处理（而不是丢弃）
  const createDebouncedEventHandler = useCallback((handler: (payload: any) => void, delayMs: number = 500) => {
    const payloadsRef = useRef<any[]>([])

    return (payload: any) => {
      // 积累所有在延迟窗口内的事件
      payloadsRef.current.push(payload)

      // 清除之前的计时器
      if (eventDebounceRef.current.timer) {
        clearTimeout(eventDebounceRef.current.timer)
      }

      // 设置新的延迟处理：处理所有积累的事件
      eventDebounceRef.current.timer = setTimeout(() => {
        const payloads = payloadsRef.current
        payloadsRef.current = []

        console.debug(`[ActivityView] 处理积累的${payloads.length}个事件`)

        // 处理最新的事件（通常包含最新的状态）
        // 如果有多个更新，最后一个通常包含最新的完整数据
        if (payloads.length > 0) {
          handler(payloads[payloads.length - 1])
        }
      }, delayMs)
    }
  }, [])

  // 监听活动更新事件：增量更新而不是全量刷新
  const handleActivityUpdated = useCallback(
    (payload: any) => {
      if (!payload || !payload.data) {
        console.warn('[ActivityView] 收到的活动数据格式不正确', payload)
        return
      }

      const updatedActivity = payload.data
      console.debug('[ActivityView] 收到活动更新事件:', updatedActivity.id)

      const { updated, dateChanged } = applyActivityUpdate(updatedActivity)

      if (!updated) {
        console.debug('[ActivityView] 活动未发生有效变化，跳过更新:', updatedActivity.id)
        return
      }

      if (dateChanged) {
        void fetchActivityCountByDate()
      }
    },
    [applyActivityUpdate, fetchActivityCountByDate]
  )

  // 监听活动删除事件：从时间线中移除
  const handleActivityDeleted = useCallback(
    (payload: any) => {
      if (!payload || !payload.data) {
        console.warn('[ActivityView] 收到的删除数据格式不正确', payload)
        return
      }

      const deletedId = payload.data.id
      console.debug('[ActivityView] 收到活动删除事件:', deletedId)

      // 从时间线中删除该活动
      // 注意：删除操作不会影响无限滚动状态（hasMore、offset 等）
      // 这些状态只在主动加载数据时更新
      setTimelineData((prevData) => {
        const result = prevData
          .map((day) => ({
            ...day,
            activities: day.activities.filter((activity) => activity.id !== deletedId)
          }))
          .filter((day) => day.activities.length > 0) // 删除空的日期块

        console.debug('[ActivityView] 删除活动后，剩余日期块数量:', result.length)
        return result
      })
    },
    [setTimelineData]
  )

  // 监听批量更新完成事件：刷新时间线（多个活动更新时）
  const handleBulkUpdateCompleted = useCallback(
    (payload: any) => {
      console.debug('[ActivityView] 收到批量更新完成事件，更新数量:', payload.data?.updatedCount)

      // 重要：只有在用户处于最新位置时才触发刷新
      // 如果用户在浏览历史数据，不应该打断他们
      if (isAtLatest) {
        console.debug('[ActivityView] 用户在最新位置，执行批量更新刷新')
        handleRefresh()
      } else {
        console.debug('[ActivityView] 用户不在最新位置，跳过批量更新刷新，避免打断浏览')
      }
    },
    [isAtLatest, handleRefresh]
  )

  // 包装事件处理函数，添加去抖
  const debouncedHandleActivityUpdated = createDebouncedEventHandler(handleActivityUpdated, 300)
  const debouncedHandleActivityDeleted = createDebouncedEventHandler(handleActivityDeleted, 300)

  useActivityUpdated(debouncedHandleActivityUpdated)
  useActivityDeleted(debouncedHandleActivityDeleted)
  useBulkUpdateCompleted(handleBulkUpdateCompleted)

  // 清理去抖计时器
  useEffect(() => {
    return () => {
      if (eventDebounceRef.current.timer) {
        clearTimeout(eventDebounceRef.current.timer)
      }
    }
  }, [])

  // 仅在组件挂载时初始化加载一次
  useEffect(() => {
    if (!initialized) {
      console.debug('[ActivityView] 首次初始化加载')
      fetchTimelineData({ limit: 15 })
      setInitialized(true)
    }
  }, [initialized, fetchTimelineData])

  if (loading && !initialized) {
    return <LoadingPage message={t('activity.loadingData')} />
  }

  return (
    <div className="flex h-full flex-col">
      {/* 固定的头部区域 - 始终显示标题和按钮 */}
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
              disabled={isRefreshing || loading || loadingMore}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              {isRefreshing ? t('common.loading') : t('common.refresh')}
            </Button>
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      {timelineData.length === 0 && !loading && !isRefreshing ? (
        // 空状态（仅在不加载时显示）
        <div className="flex flex-1 items-center justify-center p-6">
          <EmptyState icon={Clock} title={t('activity.noData')} description={t('activity.noDataDescription')} />
        </div>
      ) : timelineData.length === 0 && (loading || isRefreshing) ? (
        // 数据加载中
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
            <p className="text-muted-foreground text-sm">{t('activity.loadingData')}</p>
          </div>
        </div>
      ) : (
        // 时间线内容
        <div
          ref={(el) => {
            containerRef.current = el
            scrollContainerRef.current = el
          }}
          className="flex-1 overflow-y-auto p-6">
          {/* 顶部哨兵 - 用于 Intersection Observer */}
          <div ref={sentinelTopRef} className="h-px w-full" aria-label="Load more top trigger" />

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
          <div ref={sentinelBottomRef} className="h-px w-full" aria-label="Load more bottom trigger" />
        </div>
      )}
    </div>
  )
}
