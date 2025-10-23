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
  const checkIntervalRef = useRef<NodeJS.Timeout | null>(null)
  // 保存最新的回调，避免依赖项频繁变化
  const onLoadMoreRef = useRef(onLoadMore)

  useEffect(() => {
    onLoadMoreRef.current = onLoadMore
  }, [onLoadMore])

  // 手动检查哨兵元素是否在视口内（用于加载完成后的重新检测）
  const checkSentinelIntersection = () => {
    const container = containerRef.current
    const sentinelTop = sentinelTopRef.current
    const sentinelBottom = sentinelBottomRef.current

    if (!container || !sentinelTop || !sentinelBottom) return

    const checkSentinel = (sentinel: HTMLElement, direction: 'top' | 'bottom') => {
      const rect = sentinel.getBoundingClientRect()
      const containerRect = container.getBoundingClientRect()

      // 检查哨兵元素是否在容器的视口内
      const isVisible = rect.bottom > containerRect.top - threshold && rect.top < containerRect.bottom + threshold

      if (isVisible && !isLoadingRef.current) {
        console.debug(`[useInfiniteScroll] 手动检测到${direction === 'top' ? '顶部' : '底部'}哨兵在视口内`)
        if (direction === 'top') {
          isLoadingRef.current = true
          Promise.resolve(onLoadMoreRef.current('top')).finally(() => {
            isLoadingRef.current = false
          })
        } else {
          isLoadingRef.current = true
          Promise.resolve(onLoadMoreRef.current('bottom')).finally(() => {
            isLoadingRef.current = false
          })
        }
      }
    }

    checkSentinel(sentinelTop, 'top')
    checkSentinel(sentinelBottom, 'bottom')
  }

  // 初始化并监听容器 - 仅在 threshold 变化时重新初始化
  useEffect(() => {
    // 轮询等待容器挂载（最多等待 50 次，每次 100ms）
    let attempts = 0
    const maxAttempts = 50

    const initializeObserver = () => {
      const container = containerRef.current
      const sentinelTop = sentinelTopRef.current
      const sentinelBottom = sentinelBottomRef.current

      if (!container || !sentinelTop || !sentinelBottom) {
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(initializeObserver, 100)
        } else {
          console.error('[useInfiniteScroll] 超时：容器或哨兵元素未挂载')
        }
        return
      }

      console.log('[useInfiniteScroll] 初始化成功，容器:', {
        tagName: container.tagName,
        className: container.className,
        scrollHeight: container.scrollHeight,
        clientHeight: container.clientHeight
      })

      // 清理旧的观察器
      if (observerRef.current) {
        observerRef.current.disconnect()
      }

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

          console.debug('[useInfiniteScroll] 观察器回调', {
            target: isTopSentinel ? 'top' : 'bottom',
            isIntersecting: entry.isIntersecting,
            isLoading: isLoadingRef.current,
            intersectionRatio: entry.intersectionRatio
          })

          // 只在目标进入视口且不在加载时触发
          if (!entry.isIntersecting || isLoadingRef.current) return

          if (isTopSentinel) {
            console.warn('[useInfiniteScroll] 🔥 触顶，加载上面的数据')
            isLoadingRef.current = true
            Promise.resolve(onLoadMoreRef.current('top')).finally(() => {
              isLoadingRef.current = false
            })
          } else if (isBottomSentinel) {
            console.warn('[useInfiniteScroll] 🔥 触底，加载下面的数据')
            isLoadingRef.current = true
            Promise.resolve(onLoadMoreRef.current('bottom')).finally(() => {
              isLoadingRef.current = false
            })
          }
        })
      }

      observerRef.current = new IntersectionObserver(handleIntersection, observerOptions)

      // 观察哨兵元素
      console.debug('[useInfiniteScroll] 开始观察哨兵元素')
      observerRef.current.observe(sentinelTop)
      observerRef.current.observe(sentinelBottom)

      // 启动定期检查（每 500ms 检查一次），确保即使哨兵元素仍在视口内也能继续加载
      if (checkIntervalRef.current) clearInterval(checkIntervalRef.current)
      checkIntervalRef.current = setInterval(checkSentinelIntersection, 500)
    }

    initializeObserver()

    return () => {
      console.debug('[useInfiniteScroll] 清理观察器和定期检查')
      observerRef.current?.disconnect()
      if (checkIntervalRef.current) clearInterval(checkIntervalRef.current)
    }
  }, [threshold, checkSentinelIntersection])

  return {
    containerRef,
    sentinelTopRef,
    sentinelBottomRef
  }
}
