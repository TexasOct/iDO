import { useState, useEffect } from 'react'
import { Action } from '@/lib/types/activity'
import { TimeDisplay } from '@/components/shared/TimeDisplay'
import { ChevronDown, ChevronRight, Image as ImageIcon, Tag, Loader2 } from 'lucide-react'
import { getCachedImages } from '@/lib/client/apiClient'

interface ActionCardProps {
  action: Action
  isExpanded?: boolean
  onToggleExpand?: () => void
}

/**
 * Convert screenshot data to displayable URL
 * Handles both base64 data and hash values
 */
const toImageUrl = (value: string): string => {
  // Already a data URL
  if (value.startsWith('data:')) {
    return value
  }
  // Base64 data without prefix
  if (value.match(/^[A-Za-z0-9+/=]+$/) && value.length > 100) {
    return `data:image/jpeg;base64,${value}`
  }
  // Otherwise, return empty string (will be loaded via API)
  return ''
}

export function ActionCard({ action, isExpanded = false, onToggleExpand }: ActionCardProps) {
  const [expandedScreenshots, setExpandedScreenshots] = useState(false)
  const [screenshotDataUrls, setScreenshotDataUrls] = useState<Record<string, string>>({})
  const [loadingScreenshots, setLoadingScreenshots] = useState(false)

  const hasScreenshots = action.screenshots && action.screenshots.length > 0
  const hasKeywords = action.keywords && action.keywords.length > 0

  // Load screenshot images when expanded
  useEffect(() => {
    if (!expandedScreenshots || !hasScreenshots) {
      return
    }

    // Check if we need to load any screenshots
    const hashesToLoad = action.screenshots!.filter((hash) => {
      const url = toImageUrl(hash)
      return !url && !screenshotDataUrls[hash]
    })

    if (hashesToLoad.length === 0) {
      return
    }

    // Load screenshots from backend
    const loadScreenshots = async () => {
      setLoadingScreenshots(true)
      try {
        const response = await getCachedImages({ hashes: hashesToLoad })
        if (response.success && response.images) {
          const newDataUrls: Record<string, string> = {}
          for (const [hash, base64Data] of Object.entries(response.images)) {
            const dataStr = String(base64Data)
            newDataUrls[hash] = dataStr.startsWith('data:') ? dataStr : `data:image/jpeg;base64,${dataStr}`
          }
          setScreenshotDataUrls((prev) => ({ ...prev, ...newDataUrls }))
        }
      } catch (error) {
        console.error('[ActionCard] Failed to load screenshots:', error)
      } finally {
        setLoadingScreenshots(false)
      }
    }

    void loadScreenshots()
  }, [expandedScreenshots, hasScreenshots, action.screenshots, screenshotDataUrls])

  return (
    <div className="border-border bg-card/50 relative rounded-md border p-3 transition-all hover:shadow-sm">
      {/* Timestamp and Screenshots button - absolutely positioned */}
      <div className="absolute top-2 right-2 flex items-center gap-2">
        <div className="text-muted-foreground text-xs whitespace-nowrap">
          <TimeDisplay timestamp={action.timestamp} />
        </div>

        {/* Screenshots button */}
        {hasScreenshots && (
          <button
            onClick={() => setExpandedScreenshots(!expandedScreenshots)}
            className="text-muted-foreground hover:bg-accent hover:text-accent-foreground flex items-center gap-1 rounded-sm px-2 py-1 text-xs transition-colors">
            <ImageIcon className="h-3 w-3" />
            <span>
              {action.screenshots!.length} {action.screenshots!.length === 1 ? 'screenshot' : 'screenshots'}
            </span>
            {expandedScreenshots ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </button>
        )}
      </div>

      {/* Header - with right padding to avoid overlap with absolute positioned elements */}
      <div className="pr-44">
        <div className="flex items-center gap-2">
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              className="hover:bg-accent rounded p-0.5 transition-colors"
              aria-label={isExpanded ? 'Collapse' : 'Expand'}>
              {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            </button>
          )}

          <h5 className="text-foreground min-w-0 flex-1 text-sm leading-relaxed font-medium">{action.title}</h5>
        </div>

        {action.description && (
          <p className="text-muted-foreground mt-1 pl-5 text-xs leading-relaxed">{action.description}</p>
        )}
      </div>

      {/* Keywords */}
      {hasKeywords && (
        <div className="mt-2 flex flex-wrap items-center gap-1 pl-5">
          <Tag className="text-muted-foreground h-3 w-3" />
          {action.keywords.slice(0, 5).map((keyword, index) => (
            <span key={index} className="bg-accent text-accent-foreground rounded-sm px-1.5 py-0.5 text-xs">
              {keyword}
            </span>
          ))}
          {action.keywords.length > 5 && (
            <span className="text-muted-foreground text-xs">+{action.keywords.length - 5}</span>
          )}
        </div>
      )}

      {/* Screenshots Grid */}
      {hasScreenshots && expandedScreenshots && (
        <div className="mt-2">
          {loadingScreenshots ? (
            <div className="border-border text-muted-foreground flex items-center justify-center gap-2 rounded-md border border-dashed py-8 text-xs">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Loading screenshots...</span>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
              {action.screenshots!.map((screenshot, index) => {
                const imageUrl = toImageUrl(screenshot) || screenshotDataUrls[screenshot]

                return (
                  <div
                    key={index}
                    className="group border-border bg-muted relative aspect-video overflow-hidden rounded-md border">
                    {imageUrl ? (
                      <>
                        <img
                          src={imageUrl}
                          alt={`Screenshot ${index + 1}`}
                          className="h-full w-full object-cover transition-transform group-hover:scale-105"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement
                            target.style.display = 'none'
                            console.error('[ActionCard] Failed to load screenshot:', screenshot.substring(0, 50))
                          }}
                        />
                        <div className="absolute inset-0 bg-black/0 transition-colors group-hover:bg-black/10" />
                      </>
                    ) : (
                      <div className="text-muted-foreground flex h-full items-center justify-center text-xs">
                        <ImageIcon className="h-8 w-8 opacity-30" />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-border mt-2 border-t pt-2 pl-5">
          <div className="text-muted-foreground space-y-1 text-xs">
            {action.createdAt && (
              <div>
                <span className="font-medium">Created At:</span>
                <span className="ml-1">
                  <TimeDisplay timestamp={action.createdAt} showDate />
                </span>
              </div>
            )}
            <div>
              <span className="font-medium">Action ID:</span>
              <span className="ml-1 font-mono text-xs">{action.id}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
