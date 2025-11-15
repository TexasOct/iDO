/**
 * AI Response Component
 * Markdown renderer optimized for streaming AI responses
 * Based on shadcn/ui design patterns
 */

import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { CodeBlock, CodeBlockCopyButton } from './code-block'
import { Alert } from './alert'
import 'katex/dist/katex.min.css'
import { useMemo } from 'react'
import { cn } from '@/lib/utils'

interface ResponseProps {
  children: string
  parseIncompleteMarkdown?: boolean
  className?: string
}

/**
 * Parses incomplete markdown to prevent rendering issues during streaming
 */
function parseIncompleteMarkdown(markdown: string): string {
  // Complete incomplete bold/italic markers
  const boldCount = (markdown.match(/\*\*/g) || []).length
  const italicCount = (markdown.match(/(?<!\*)\*(?!\*)/g) || []).length
  const strikeCount = (markdown.match(/~~/g) || []).length

  let result = markdown

  // Close incomplete bold
  if (boldCount % 2 !== 0) {
    result += '**'
  }

  // Close incomplete italic
  if (italicCount % 2 !== 0) {
    result += '*'
  }

  // Close incomplete strikethrough
  if (strikeCount % 2 !== 0) {
    result += '~~'
  }

  // Close incomplete code blocks
  const codeBlockCount = (result.match(/```/g) || []).length
  if (codeBlockCount % 2 !== 0) {
    result += '\n```'
  }

  // Close incomplete inline code
  const inlineCodeCount = (result.match(/(?<!`)`(?!`)/g) || []).length
  if (inlineCodeCount % 2 !== 0) {
    result += '`'
  }

  // Close incomplete links
  const linkOpenCount = (result.match(/\[/g) || []).length
  const linkCloseCount = (result.match(/\]/g) || []).length
  if (linkOpenCount > linkCloseCount) {
    result += ']'
  }

  return result
}

const markdownComponents: Components = {
  // Code blocks
  code({ className, children, node, inline, ...rest }: any) {
    const isInline = !className || !className.startsWith('language-')

    if (isInline) {
      // Inline code: rely on markdown AST value to avoid stray backticks
      const astValue = node?.children?.[0]?.value
      const content =
        typeof astValue === 'string' ? astValue : Array.isArray(children) ? children.join('') : String(children ?? '')

      return (
        <code className="chat-inline-code" {...rest}>
          {content}
        </code>
      )
    }

    // Extract language
    const language = className?.replace('language-', '') || 'plaintext'
    const codeString = String(children).replace(/\n$/, '')

    return (
      <CodeBlock code={codeString} language={language}>
        <CodeBlockCopyButton />
      </CodeBlock>
    )
  },

  // Strip default pre wrapper from react-markdown to avoid duplicate backgrounds
  pre({ children }) {
    return <>{children}</>
  },

  // Paragraphs
  p({ children }) {
    return <p className="mb-3 leading-7 last:mb-0">{children}</p>
  },

  // Lists
  ul({ children }) {
    return <ul className="mb-3 ml-5 list-disc space-y-1.5 leading-7">{children}</ul>
  },
  ol({ children }) {
    return <ol className="mb-3 ml-5 list-decimal space-y-1.5 leading-7">{children}</ol>
  },
  li({ children }) {
    return <li className="pl-1.5">{children}</li>
  },

  // Links
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 underline">
        {children}
      </a>
    )
  },

  // Headings
  h1({ children }) {
    return <h1 className="mt-4 mb-2 text-2xl font-bold">{children}</h1>
  },
  h2({ children }) {
    return <h2 className="mt-3 mb-2 text-xl font-bold">{children}</h2>
  },
  h3({ children }) {
    return <h3 className="mt-2 mb-2 text-lg font-bold">{children}</h3>
  },
  h4({ children }) {
    return <h4 className="mt-2 mb-2 text-base font-bold">{children}</h4>
  },
  h5({ children }) {
    return <h5 className="mt-2 mb-2 text-sm font-bold">{children}</h5>
  },
  h6({ children }) {
    return <h6 className="mt-2 mb-2 text-xs font-bold">{children}</h6>
  },

  // Blockquotes
  blockquote({ children }) {
    return (
      <Alert className="my-4 rounded-r-lg border-y-0 border-r-0 border-l-4 border-amber-500/40 bg-amber-50/50 py-2 dark:bg-amber-950/20">
        <div className="col-span-2 col-start-1 text-sm leading-relaxed">{children}</div>
      </Alert>
    )
  },

  // Tables
  table({ children }) {
    return (
      <div className="my-4 overflow-x-auto">
        <table className="divide-border min-w-full divide-y rounded-lg border">{children}</table>
      </div>
    )
  },
  thead({ children }) {
    return <thead className="bg-muted">{children}</thead>
  },
  tbody({ children }) {
    return <tbody className="divide-border divide-y">{children}</tbody>
  },
  tr({ children }) {
    return <tr>{children}</tr>
  },
  th({ children }) {
    return <th className="px-4 py-2 text-left text-sm font-medium">{children}</th>
  },
  td({ children }) {
    return <td className="px-4 py-2 text-sm">{children}</td>
  },

  // Horizontal rule
  hr() {
    return <hr className="border-border my-4" />
  },

  // Images
  img({ src, alt, node, ...rest }) {
    if (!src) return null
    return (
      <img
        src={src}
        alt={alt ?? ''}
        loading="lazy"
        className="border-border my-4 h-auto max-w-full rounded-lg border shadow-sm"
        {...rest}
      />
    )
  }
}

export function Response({ children, parseIncompleteMarkdown: shouldParse = true, className }: ResponseProps) {
  const content = useMemo(() => (shouldParse ? parseIncompleteMarkdown(children) : children), [children, shouldParse])

  return (
    <div className={cn('warp-break-words max-w-full', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
