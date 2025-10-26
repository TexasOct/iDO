/**
 * Custom Shiki themes for code syntax highlighting
 * Matching our design system colors
 */

import type { ThemeRegistration } from 'shiki'

export const lightTheme: ThemeRegistration = {
  name: 'rewind-light',
  type: 'light',
  bg: 'var(--code-block-bg)',
  fg: 'var(--code-block-foreground)',
  colors: {
    'editor.background': 'var(--code-block-bg)',
    'editor.foreground': 'var(--code-block-foreground)'
  },
  tokenColors: [
    {
      scope: ['comment', 'punctuation.definition.comment'],
      settings: {
        foreground: '#64748b',
        fontStyle: 'italic'
      }
    },
    {
      scope: ['keyword', 'storage.type', 'storage.modifier', 'keyword.control', 'keyword.other'],
      settings: {
        foreground: '#7c3aed',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['string', 'string.quoted'],
      settings: {
        foreground: '#059669'
      }
    },
    {
      scope: ['entity.name.function', 'support.function', 'meta.function-call'],
      settings: {
        foreground: '#d97706',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['constant.numeric', 'constant.language'],
      settings: {
        foreground: '#dc2626'
      }
    },
    {
      scope: ['variable', 'support.variable', 'variable.other'],
      settings: {
        foreground: '#0891b2'
      }
    },
    {
      scope: ['entity.name.type', 'support.type', 'support.class'],
      settings: {
        foreground: '#0891b2',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['punctuation', 'meta.brace', 'keyword.operator'],
      settings: {
        foreground: '#db2777'
      }
    },
    {
      scope: ['entity.name.tag', 'meta.tag'],
      settings: {
        foreground: '#2563eb'
      }
    }
  ]
}

export const darkTheme: ThemeRegistration = {
  name: 'rewind-dark',
  type: 'dark',
  bg: 'var(--code-block-bg)',
  fg: 'var(--code-block-foreground)',
  colors: {
    'editor.background': 'var(--code-block-bg)',
    'editor.foreground': 'var(--code-block-foreground)'
  },
  tokenColors: [
    {
      scope: ['comment', 'punctuation.definition.comment'],
      settings: {
        foreground: '#718096',
        fontStyle: 'italic'
      }
    },
    {
      scope: ['keyword', 'storage.type', 'storage.modifier', 'keyword.control', 'keyword.other'],
      settings: {
        foreground: '#bb6bd9',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['string', 'string.quoted'],
      settings: {
        foreground: '#48bb78'
      }
    },
    {
      scope: ['entity.name.function', 'support.function', 'meta.function-call'],
      settings: {
        foreground: '#f6ad55',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['constant.numeric', 'constant.language'],
      settings: {
        foreground: '#ed8936'
      }
    },
    {
      scope: ['variable', 'support.variable', 'variable.other'],
      settings: {
        foreground: '#4299e1'
      }
    },
    {
      scope: ['entity.name.type', 'support.type', 'support.class'],
      settings: {
        foreground: '#4299e1',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['punctuation', 'meta.brace', 'keyword.operator'],
      settings: {
        foreground: '#ed64a6'
      }
    },
    {
      scope: ['entity.name.tag', 'meta.tag'],
      settings: {
        foreground: '#4299e1'
      }
    }
  ]
}
