import { useEffect, useRef, useState } from 'react'

interface UseScrollAnimationOptions {
  /** Threshold for triggering animation (0-1) */
  threshold?: number
  /** Root margin for early/late triggering */
  rootMargin?: string
  /** Trigger only once */
  triggerOnce?: boolean
  /** Delay in milliseconds before animation starts */
  delay?: number
}

/**
 * Custom hook for scroll-triggered animations using Intersection Observer
 * Returns a ref to attach to the element and a boolean indicating if it's visible
 */
export function useScrollAnimation<T extends HTMLElement = HTMLDivElement>(options: UseScrollAnimationOptions = {}) {
  const { threshold = 0.1, rootMargin = '0px', triggerOnce = true, delay = 0 } = options

  const elementRef = useRef<T>(null)
  const [isVisible, setIsVisible] = useState(false)
  const [hasTriggered, setHasTriggered] = useState(false)

  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    // If already triggered and triggerOnce is true, don't observe
    if (triggerOnce && hasTriggered) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            if (delay > 0) {
              setTimeout(() => {
                setIsVisible(true)
                if (triggerOnce) {
                  setHasTriggered(true)
                }
              }, delay)
            } else {
              setIsVisible(true)
              if (triggerOnce) {
                setHasTriggered(true)
              }
            }
          } else if (!triggerOnce) {
            setIsVisible(false)
          }
        })
      },
      {
        threshold,
        rootMargin
      }
    )

    observer.observe(element)

    return () => {
      observer.disconnect()
    }
  }, [threshold, rootMargin, triggerOnce, delay, hasTriggered])

  return { ref: elementRef, isVisible }
}
