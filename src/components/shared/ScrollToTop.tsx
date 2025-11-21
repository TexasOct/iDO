import { useState, useEffect } from 'react'
import { ArrowUp } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ScrollToTopProps {
  /**
   * The scrollable container element ref or selector
   * If not provided, uses window scroll
   */
  containerRef?: React.RefObject<HTMLDivElement | null>
  /**
   * Scroll offset threshold to show the button (in pixels)
   * @default 300
   */
  threshold?: number
  /**
   * Position from the right edge (Tailwind class)
   * @default 'right-6'
   */
  rightPosition?: string
  /**
   * Position from the bottom edge (Tailwind class)
   * @default 'bottom-6'
   */
  bottomPosition?: string
}

/**
 * Floating "scroll to top" button that appears when scrolling down
 * Auto-hides when at the top of the page/container
 */
export function ScrollToTop({
  containerRef,
  threshold = 300,
  rightPosition = 'right-6',
  bottomPosition = 'bottom-6'
}: ScrollToTopProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const container = containerRef?.current

    const handleScroll = () => {
      const scrollTop = container ? container.scrollTop : window.scrollY
      setIsVisible(scrollTop > threshold)
    }

    // Check initial scroll position
    handleScroll()

    if (container) {
      container.addEventListener('scroll', handleScroll)
    } else {
      window.addEventListener('scroll', handleScroll)
    }

    return () => {
      if (container) {
        container.removeEventListener('scroll', handleScroll)
      } else {
        window.removeEventListener('scroll', handleScroll)
      }
    }
  }, [containerRef, threshold])

  const scrollToTop = () => {
    if (containerRef?.current) {
      containerRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    } else {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    }
  }

  if (!isVisible) return null

  return (
    <Button
      onClick={scrollToTop}
      size="icon"
      className={`bg-primary text-primary-foreground hover:bg-primary/90 fixed z-50 h-12 w-12 rounded-full shadow-lg transition-all hover:scale-110 ${rightPosition} ${bottomPosition}`}
      aria-label="Scroll to top">
      <ArrowUp className="h-6 w-6 stroke-[2.5]" />
    </Button>
  )
}
