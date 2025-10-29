import { getCachedImages } from '@/lib/client/apiClient'

/**
 * 从后端获取指定哈希的截图（base64 格式）
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
