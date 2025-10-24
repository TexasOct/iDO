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
  const LOAD_DEBOUNCE_MS = 500 // 防抖时间：500ms 内不重复触发同一方向的加载

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

  // 初始化并监听容器 - 仅在 threshold 变化时重新初始化
  useEffect(() => {
    let isInitialized = false
    let resizeObserver: ResizeObserver | null = null

    const initializeObserver = () => {
      if (isInitialized) return // 防止重复初始化

      const container = containerRef.current
      const sentinelTop = sentinelTopRef.current
      const sentinelBottom = sentinelBottomRef.current

      if (!container || !sentinelTop || !sentinelBottom) {
        return // 元素未就绪，等待 ResizeObserver 触发重试
      }

      isInitialized = true

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

          // 只在目标进入视口时处理
          if (!entry.isIntersecting) return

          // 使用防抖逻辑防止重复触发
          if (isTopSentinel && shouldTriggerLoad('top')) {
            console.warn('[useInfiniteScroll] 🔥 触顶，加载上面的数据')
            isLoadingRef.current = true
            Promise.resolve(onLoadMoreRef.current('top')).finally(() => {
              isLoadingRef.current = false
            })
          } else if (isBottomSentinel && shouldTriggerLoad('bottom')) {
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
    }

    // 立即尝试初始化
    initializeObserver()

    // 如果元素还未挂载，使用 ResizeObserver 监听容器变化
    // 当容器被添加到 DOM 后，它的尺寸会改变，触发 ResizeObserver
    if (!isInitialized && containerRef.current) {
      try {
        resizeObserver = new ResizeObserver(() => {
          if (!isInitialized) {
            initializeObserver()
          }
          // 元素挂载后清理 ResizeObserver
          if (isInitialized && resizeObserver) {
            resizeObserver.disconnect()
            resizeObserver = null
          }
        })
        resizeObserver.observe(containerRef.current)
      } catch (e) {
        console.debug('[useInfiniteScroll] ResizeObserver 不可用，使用备用方案')
      }
    }

    return () => {
      console.debug('[useInfiniteScroll] 清理观察器')
      observerRef.current?.disconnect()
      resizeObserver?.disconnect()
    }
  }, [threshold])

  return {
    containerRef,
    sentinelTopRef,
    sentinelBottomRef
  }
}
