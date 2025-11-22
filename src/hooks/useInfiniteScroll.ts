import { useEffect, useRef } from 'react'

interface UseInfiniteScrollOptions {
  onLoadMore: (direction: 'top' | 'bottom') => void | Promise<void>
  threshold?: number // Trigger distance (default: 300px)
}

/**
 * Bidirectional infinite scroll hook.
 * Uses the Intersection Observer API to watch sentinel elements at the top and bottom.
 * Capabilities:
 * 1. Automatically loads more data when either sentinel is reached.
 * 2. Keeps a capped number of elements in the container, trimming from the opposite side.
 */
export function useInfiniteScroll({ onLoadMore, threshold = 300 }: UseInfiniteScrollOptions) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sentinelTopRef = useRef<HTMLDivElement>(null)
  const sentinelBottomRef = useRef<HTMLDivElement>(null)
  const isLoadingRef = useRef(false)
  const observerRef = useRef<IntersectionObserver | null>(null)
  // Keep the latest callback to avoid extra dependencies
  const onLoadMoreRef = useRef(onLoadMore)
  // Track the last trigger time per direction to prevent rapid firing
  const lastLoadTimeRef = useRef<{ top: number; bottom: number }>({ top: 0, bottom: 0 })
  const LOAD_DEBOUNCE_MS = 200 // Debounce window so we do not trigger twice in 200ms for the same direction
  // Flag whether the observer has been initialized
  const isInitializedRef = useRef(false)
  // Cache a pending direction to continue loading once the current run finishes
  const pendingLoadRef = useRef<'top' | 'bottom' | null>(null)

  useEffect(() => {
    onLoadMoreRef.current = onLoadMore
  }, [onLoadMore])

  // Determine if the load should trigger (debounce logic)
  const shouldTriggerLoad = (direction: 'top' | 'bottom'): boolean => {
    if (isLoadingRef.current) {
      return false
    }

    const now = Date.now()
    const lastLoadTime = lastLoadTimeRef.current[direction]
    const timeSinceLastLoad = now - lastLoadTime

    // Skip if we are still inside the debounce window for this direction
    if (timeSinceLastLoad < LOAD_DEBOUNCE_MS) {
      return false
    }

    // Update the last load timestamp for the direction
    lastLoadTimeRef.current[direction] = now
    return true
  }

  // Poll for element readiness and initialize observers
  useEffect(() => {
    // Recursively check if the sentinel is visible and keep loading as needed
    const checkAndLoadMore = (direction: 'top' | 'bottom') => {
      if (isLoadingRef.current) {
        return
      }

      const sentinel = direction === 'top' ? sentinelTopRef.current : sentinelBottomRef.current
      const container = containerRef.current

      if (!sentinel || !container) {
        return
      }

      // Determine whether the sentinel is within the container viewport
      const containerRect = container.getBoundingClientRect()
      const sentinelRect = sentinel.getBoundingClientRect()

      const isVisible =
        sentinelRect.top >= containerRect.top &&
        sentinelRect.bottom <= containerRect.bottom &&
        sentinelRect.left >= containerRect.left &&
        sentinelRect.right <= containerRect.right

      if (isVisible && shouldTriggerLoad(direction)) {
        console.warn(
          `[useInfiniteScroll] Sentinel still visible, continue loading ${
            direction === 'top' ? 'previous' : 'next'
          } data`
        )
        isLoadingRef.current = true

        Promise.resolve(onLoadMoreRef.current(direction)).finally(() => {
          isLoadingRef.current = false
          // After each load, check if the sentinel remains visible
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

      // Decide if the observer needs to be reinitialized
      // If we already have one, disconnect it before reusing
      if (observerRef.current) {
        // Disconnect the old observer before wiring up the new elements
        console.debug('[useInfiniteScroll] Cleaning up old observer')
        observerRef.current.disconnect()
      }

      console.log('[useInfiniteScroll] Initializing Intersection Observer')

      // Use the container as the Intersection Observer root
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

          console.warn('[useInfiniteScroll] Observer callback', {
            target: isTopSentinel ? 'top' : 'bottom',
            isIntersecting: entry.isIntersecting,
            isLoading: isLoadingRef.current
          })

          // Only handle cases where the sentinel enters the viewport
          if (!entry.isIntersecting) return

          const direction = isTopSentinel ? 'top' : 'bottom'

          // If loading is in progress, store the pending direction
          if (isLoadingRef.current) {
            console.debug('[useInfiniteScroll] Loading in progress, storing pending direction:', direction)
            pendingLoadRef.current = direction
            return
          }

          // Use debounce logic to avoid duplicate triggers
          if (shouldTriggerLoad(direction)) {
            console.warn(
              `[useInfiniteScroll] 🔥 Hit ${direction === 'top' ? 'top' : 'bottom'}, loading ${direction === 'top' ? 'previous' : 'next'} data`
            )
            isLoadingRef.current = true

            Promise.resolve(onLoadMoreRef.current(direction)).finally(() => {
              isLoadingRef.current = false

              // After loading completes, check for pending directions
              if (pendingLoadRef.current) {
                const pendingDirection = pendingLoadRef.current
                pendingLoadRef.current = null

                console.debug('[useInfiniteScroll] Load complete, handling pending direction:', pendingDirection)

                // Use setTimeout to let the DOM update, then check recursively
                setTimeout(() => {
                  checkAndLoadMore(pendingDirection)
                }, 50)
              } else {
                // Even without pending work, re-check the sentinel for this direction
                setTimeout(() => {
                  checkAndLoadMore(direction)
                }, 50)
              }
            })
          }
        })
      }

      observerRef.current = new IntersectionObserver(handleIntersection, observerOptions)

      // Start observing the sentinel elements
      console.debug('[useInfiniteScroll] Start observing sentinel elements')
      observerRef.current.observe(sentinelTop)
      observerRef.current.observe(sentinelBottom)

      isInitializedRef.current = true
      return true
    }

    // Attempt immediate initialization
    initializeObserver()

    // Keep polling to detect re-mounted or changed elements
    // Handles re-renders caused by data updates
    const pollInterval = setInterval(() => {
      // Check whether the observer remains valid
      // Reinitialize if elements were recreated
      const container = containerRef.current
      const sentinelTop = sentinelTopRef.current
      const sentinelBottom = sentinelBottomRef.current

      if (container && sentinelTop && sentinelBottom) {
        // Reinitialize when no observer exists or the flag is reset
        if (!observerRef.current || !isInitializedRef.current) {
          console.debug('[useInfiniteScroll] Element change detected, reinitializing')
          initializeObserver()
        }
      }
    }, 500) // Check every 500 ms

    return () => {
      clearInterval(pollInterval)
      console.debug('[useInfiniteScroll] Cleaning observer and polling')
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
