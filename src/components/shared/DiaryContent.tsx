import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { fetchActivityDetails } from '@/lib/services/activity/db'
import { isTauri } from '@/lib/utils/tauri'

const ACTIVITY_RE = /\[activity:([^\]]+)\]([\s\S]*?)\[\/activity\]/gi

type TitleMap = Record<string, string>

function truncate(text: string, max = 32) {
  const s = text.replace(/\s+/g, ' ').trim()
  return s.length > max ? s.slice(0, max) + '…' : s
}

export default function DiaryContent({ text }: { text: string }) {
  const { t } = useTranslation()
  const [titles, setTitles] = useState<TitleMap>({})
  const cacheRef = useRef<Map<string, string>>(new Map())

  const { nodes, refs, ids } = useMemo(() => {
    const nodes: React.ReactNode[] = []
    const refs: { index: number; id: string; fallback: string }[] = []
    const idToIndex = new Map<string, number>()
    const ids: string[] = []

    let lastIndex = 0
    let match: RegExpExecArray | null
    ACTIVITY_RE.lastIndex = 0

    while ((match = ACTIVITY_RE.exec(text)) !== null) {
      const [full, id, inner] = match
      const start = match.index
      const end = start + full.length

      if (lastIndex < start) {
        nodes.push(text.slice(lastIndex, start))
      }

      let index = idToIndex.get(id)
      if (!index) {
        index = refs.length + 1
        idToIndex.set(id, index)
        ids.push(id)
        refs.push({ index, id, fallback: truncate(inner) })
      }

      nodes.push(
        <span key={`seg-${start}`}>
          {inner}
          <sup id={`cite-${index}`} className="ml-0.5 align-super text-[0.75em] opacity-60">
            <a href={`#ref-${index}`} className="decoration-dotted hover:underline">
              [{index}]
            </a>
          </sup>
        </span>
      )

      lastIndex = end
    }

    if (lastIndex < text.length) {
      nodes.push(text.slice(lastIndex))
    }

    return { nodes, refs, ids }
  }, [text])

  useEffect(() => {
    if (!isTauri()) return // Avoid calling Tauri APIs in plain web dev
    let cancelled = false
    const missing = ids.filter((id) => !cacheRef.current.has(id))
    if (missing.length === 0) return
    ;(async () => {
      const entries: [string, string][] = []
      for (const id of missing) {
        try {
          const detail = await fetchActivityDetails(id)
          const title = (detail?.title || detail?.description || '').trim()
          if (title) {
            entries.push([id, title])
          }
        } catch {
          // ignore fetch errors; will fallback to inner content
        }
      }
      if (!cancelled && entries.length) {
        const map = new Map(cacheRef.current)
        for (const [id, title] of entries) map.set(id, title)
        cacheRef.current = map
        const obj: TitleMap = {}
        for (const [k, v] of map.entries()) obj[k] = v
        setTitles(obj)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [ids])

  if (refs.length === 0) {
    return <p className="text-muted-foreground text-sm leading-6 whitespace-pre-wrap">{text}</p>
  }

  const referencesLabel = t('common.references', (t as any)?.i18n?.language?.startsWith('zh') ? '引用' : 'References')

  return (
    <div>
      <div className="text-muted-foreground text-sm leading-6 whitespace-pre-wrap">{nodes}</div>
      <div className="mt-2">
        <div className="mb-0.5 text-xs font-normal opacity-60">{referencesLabel}</div>
        <ol className="text-muted-foreground/80 m-0 list-decimal pl-4 text-xs">
          {refs.map(({ index, id, fallback }) => (
            <li key={id} id={`ref-${index}`} className="my-0.5">
              <a href={`#cite-${index}`} aria-label="jump to cite" className="mr-1 opacity-50 hover:opacity-80">
                ^
              </a>
              <Link to={`/activity?focus=${encodeURIComponent(id)}`} className="decoration-dotted hover:underline">
                {titles[id] ? titles[id] : fallback}
              </Link>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
