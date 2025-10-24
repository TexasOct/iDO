import { useEffect, useRef } from 'react'

interface UseInfiniteScrollOptions {
  onLoadMore: (direction: 'top' | 'bottom') => void | Promise<void>
  threshold?: number // 触发距离（默认: 300px）
}

/**
 * 双向无限滚动 hook
 * 使用 Intersection Observer API 检测顶部和底部哨兵元素
 * 实现：
 * 1. 触顶/触底时自动加载更多数据
 * 2. 容器内最多保持指定数量元素，超过时从反向位置卸载
 */
export function useInfiniteScroll({ onLoadMore, threshold = 300 }: UseInfiniteScrollOptions) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sentinelTopRef = useRef<HTMLDivElement>(null)
  const sentinelBottomRef = useRef<HTMLDivElement>(null)
  const isLoadingRef = useRef(false)
  const observerRef = useRef<IntersectionObserver | null>(null)
  // 保存最新的回调，避免依赖项频繁变化
  const onLoadMoreRef = useRef(onLoadMore)
  // 追踪上次加载的时间和方向，防止短时间内重复触发
  const lastLoadTimeRef = useRef<{ top: number; bottom: number }>({ top: 0, bottom: 0 })
  const LOAD_DEBOUNCE_MS = 200 // 防抖时间：200ms 内不重复触发同一方向的加载（降低以支持快速滚动）
  // 标记是否已经初始化过
  const isInitializedRef = useRef(false)
  // 保存待处理的加载方向，用于在当前加载完成后继续加载
  const pendingLoadRef = useRef<'top' | 'bottom' | null>(null)

  useEffect(() => {
    onLoadMoreRef.current = onLoadMore
  }, [onLoadMore])

  // 检查是否应该触发加载（防抖逻辑）
  const shouldTriggerLoad = (direction: 'top' | 'bottom'): boolean => {
    if (isLoadingRef.current) {
      return false
    }

    const now = Date.now()
    const lastLoadTime = lastLoadTimeRef.current[direction]
    const timeSinceLastLoad = now - lastLoadTime

    // 如果距离上次加载不到 LOAD_DEBOUNCE_MS，则不触发
    if (timeSinceLastLoad < LOAD_DEBOUNCE_MS) {
      return false
    }

    // 更新最后加载时间
    lastLoadTimeRef.current[direction] = now
    return true
  }

  // 使用 polling 方式检测元素就绪并初始化
  useEffect(() => {
    // 检查哨兵元素是否在视口内，如果在则继续加载（递归）
    const checkAndLoadMore = (direction: 'top' | 'bottom') => {
      if (isLoadingRef.current) {
        return
      }

      const sentinel = direction === 'top' ? sentinelTopRef.current : sentinelBottomRef.current
      const container = containerRef.current

      if (!sentinel || !container) {
        return
      }

      // 检查哨兵是否在容器视口内
      const containerRect = container.getBoundingClientRect()
      const sentinelRect = sentinel.getBoundingClientRect()

      const isVisible =
        sentinelRect.top >= containerRect.top &&
        sentinelRect.bottom <= containerRect.bottom &&
        sentinelRect.left >= containerRect.left &&
        sentinelRect.right <= containerRect.right

      if (isVisible && shouldTriggerLoad(direction)) {
        console.warn(`[useInfiniteScroll] 哨兵仍然可见，继续加载${direction === 'top' ? '上面' : '下面'}的数据`)
        isLoadingRef.current = true

        Promise.resolve(onLoadMoreRef.current(direction)).finally(() => {
          isLoadingRef.current = false
          // 递归检查：加载完成后再次检查哨兵是否仍然可见
          setTimeout(() => {
            checkAndLoadMore(direction)
          }, 50)
        })
      }
    }

    const initializeObserver = () => {
      const container = containerRef.current
      const sentinelTop = sentinelTopRef.current
      const sentinelBottom = sentinelBottomRef.current

      if (!container || !sentinelTop || !sentinelBottom) {
        return false
      }

      // 防止重复初始化
      if (isInitializedRef.current && observerRef.current) {
        return true
      }

      // 清理旧的观察器
      if (observerRef.current) {
        observerRef.current.disconnect()
      }

      console.log('[useInfiniteScroll] 初始化 Intersection Observer')

      // 使用容器作为 root
      const observerOptions: IntersectionObserverInit = {
        root: container,
        rootMargin: `${threshold}px 0px ${threshold}px 0px`,
        threshold: [0, 1]
      }

      const handleIntersection = (entries: IntersectionObserverEntry[]) => {
        entries.forEach((entry) => {
          const isTopSentinel = entry.target === sentinelTopRef.current
          const isBottomSentinel = entry.target === sentinelBottomRef.current

          if (!isTopSentinel && !isBottomSentinel) return

          console.warn('[useInfiniteScroll] 观察器回调', {
            target: isTopSentinel ? 'top' : 'bottom',
            isIntersecting: entry.isIntersecting,
            isLoading: isLoadingRef.current
          })

          // 只在目标进入视口时处理
          if (!entry.isIntersecting) return

          const direction = isTopSentinel ? 'top' : 'bottom'

          // 如果正在加载，记录待处理的方向
          if (isLoadingRef.current) {
            console.debug('[useInfiniteScroll] 正在加载，记录待处理方向:', direction)
            pendingLoadRef.current = direction
            return
          }

          // 使用防抖逻辑防止重复触发
          if (shouldTriggerLoad(direction)) {
            console.warn(
              `[useInfiniteScroll] 🔥 触${direction === 'top' ? '顶' : '底'}，加载${direction === 'top' ? '上面' : '下面'}的数据`
            )
            isLoadingRef.current = true

            Promise.resolve(onLoadMoreRef.current(direction)).finally(() => {
              isLoadingRef.current = false

              // 加载完成后，检查是否有待处理的加载请求
              if (pendingLoadRef.current) {
                const pendingDirection = pendingLoadRef.current
                pendingLoadRef.current = null

                console.debug('[useInfiniteScroll] 加载完成，处理待处理的方向:', pendingDirection)

                // 使用 setTimeout 确保 DOM 已更新，然后递归检查并加载
                setTimeout(() => {
                  checkAndLoadMore(pendingDirection)
                }, 50)
              } else {
                // 即使没有待处理的请求，也检查当前方向的哨兵是否仍然可见
                setTimeout(() => {
                  checkAndLoadMore(direction)
                }, 50)
              }
            })
          }
        })
      }

      observerRef.current = new IntersectionObserver(handleIntersection, observerOptions)

      // 观察哨兵元素
      console.debug('[useInfiniteScroll] 开始观察哨兵元素')
      observerRef.current.observe(sentinelTop)
      observerRef.current.observe(sentinelBottom)

      isInitializedRef.current = true
      return true
    }

    // 尝试立即初始化
    if (initializeObserver()) {
      return
    }

    // 如果初始化失败，使用 polling 检测元素就绪
    console.debug('[useInfiniteScroll] 元素未就绪，启动 polling')
    const pollInterval = setInterval(() => {
      if (initializeObserver()) {
        console.debug('[useInfiniteScroll] Polling 成功，清除 interval')
        clearInterval(pollInterval)
      }
    }, 100)

    return () => {
      clearInterval(pollInterval)
      console.debug('[useInfiniteScroll] 清理观察器')
      observerRef.current?.disconnect()
      observerRef.current = null
      isInitializedRef.current = false
    }
  }, [threshold])

  return {
    containerRef,
    sentinelTopRef,
    sentinelBottomRef
  }
}
