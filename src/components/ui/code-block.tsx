/**
 * Code Block Component for AI Responses
 * Based on shadcn/ui design patterns with Shiki syntax highlighting
 */

import { createContext, useContext, useState, useEffect } from 'react'
import { Check, Copy } from 'lucide-react'
import { codeToHtml } from 'shiki'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { lightTheme, darkTheme } from '@/lib/themes/code-themes'

interface CodeBlockContextValue {
  code: string
}

const CodeBlockContext = createContext<CodeBlockContextValue | null>(null)

function useCodeBlock() {
  const context = useContext(CodeBlockContext)
  if (!context) {
    throw new Error('useCodeBlock must be used within a CodeBlock')
  }
  return context
}

interface CodeBlockProps {
  code: string
  language?: string
  children?: React.ReactNode
  className?: string
}

export function CodeBlock({ code, language = 'plaintext', children, className }: CodeBlockProps) {
  const [lightHtml, setLightHtml] = useState<string>('')
  const [darkHtml, setDarkHtml] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function highlight() {
      try {
        setIsLoading(true)

        // Generate highlighted code for both themes with our custom colors
        const [light, dark] = await Promise.all([
          codeToHtml(code, {
            lang: language,
            theme: lightTheme,
            colorReplacements: {
              '#f8fafc': 'var(--code-block-bg)',
              '#1e293b': 'var(--code-block-foreground)'
            }
          }),
          codeToHtml(code, {
            lang: language,
            theme: darkTheme,
            colorReplacements: {
              '#1a202c': 'var(--code-block-bg)',
              '#e2e8f0': 'var(--code-block-foreground)'
            }
          })
        ])

        if (!cancelled) {
          setLightHtml(light)
          setDarkHtml(dark)
          setIsLoading(false)
        }
      } catch (error) {
        console.error('Syntax highlighting error:', error)
        // Fallback to plain text
        if (!cancelled) {
          const fallback = `<pre><code>${code}</code></pre>`
          setLightHtml(fallback)
          setDarkHtml(fallback)
          setIsLoading(false)
        }
      }
    }

    highlight()

    return () => {
      cancelled = true
    }
  }, [code, language])

  return (
    <CodeBlockContext.Provider value={{ code }}>
      <div className={cn('code-block-container group', className)}>
        {/* Header */}
        {(language !== 'plaintext' || children) && (
          <div className="code-block-header">
            {language !== 'plaintext' && <span className="code-block-language">{language}</span>}
            <div className="ml-auto flex items-center gap-2">{children}</div>
          </div>
        )}

        {/* Code Content */}
        <div className="code-block-content">
          {isLoading ? (
            <pre className="m-0 p-5">
              <code className="text-sm">{code}</code>
            </pre>
          ) : (
            <>
              {/* Light Theme */}
              <div className="shiki-wrapper dark:hidden" dangerouslySetInnerHTML={{ __html: lightHtml }} />
              {/* Dark Theme */}
              <div className="shiki-wrapper hidden dark:block" dangerouslySetInnerHTML={{ __html: darkHtml }} />
            </>
          )}
        </div>
      </div>
    </CodeBlockContext.Provider>
  )
}

interface CodeBlockCopyButtonProps {
  onCopy?: () => void
  onError?: (error: Error) => void
  timeout?: number
}

export function CodeBlockCopyButton({ onCopy, onError, timeout = 2000 }: CodeBlockCopyButtonProps) {
  const { code } = useCodeBlock()
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      onCopy?.()
      setTimeout(() => setCopied(false), timeout)
    } catch (error) {
      onError?.(error as Error)
    }
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleCopy}
      className="h-7 px-2 text-xs opacity-0 transition-opacity group-hover:opacity-100">
      {copied ? (
        <>
          <Check className="mr-1.5 h-3.5 w-3.5" />
          Copied
        </>
      ) : (
        <>
          <Copy className="mr-1.5 h-3.5 w-3.5" />
          Copy
        </>
      )}
    </Button>
  )
}
