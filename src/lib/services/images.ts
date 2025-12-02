import { getCachedImages } from '@/lib/client/apiClient'

/**
 * Get the screenshot with the specified hash from the backend (in base64 format)
 */
export async function fetchImageBase64ByHash(hash?: string): Promise<string | null> {
  if (!hash) {
    return null
  }

  try {
    const response = await getCachedImages({ hashes: [hash] })
    if (response.success) {
      const images = response.images as Record<string, unknown> | undefined
      const image = images?.[hash]
      if (typeof image === 'string' && image.length > 0) {
        return image
      }
    }
  } catch (error) {
    console.error('[fetchImageBase64ByHash] Failed to fetch image:', error)
  }

  return null
}
