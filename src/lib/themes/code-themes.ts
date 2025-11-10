/**
 * Custom Shiki themes for code syntax highlighting
 * Matching our design system colors
 */

import type { ThemeRegistration } from 'shiki'

export const lightTheme: ThemeRegistration = {
  name: 'ido-light',
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
        foreground: '#a5adba',
        fontStyle: 'italic'
      }
    },
    {
      scope: ['keyword', 'storage.type', 'storage.modifier', 'keyword.control', 'keyword.other'],
      settings: {
        foreground: '#6c6fdf',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['string', 'string.quoted', 'string.template'],
      settings: {
        foreground: '#2fad74'
      }
    },
    {
      scope: ['entity.name.function', 'support.function', 'meta.function-call'],
      settings: {
        foreground: '#3f82d9',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['constant.numeric', 'constant.language', 'constant.other'],
      settings: {
        foreground: '#d97745'
      }
    },
    {
      scope: ['variable', 'support.variable', 'variable.other'],
      settings: {
        foreground: '#3aa6a1'
      }
    },
    {
      scope: ['entity.name.type', 'support.type', 'support.class', 'support.interface'],
      settings: {
        foreground: '#3aa0c6',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['punctuation', 'meta.brace', 'keyword.operator'],
      settings: {
        foreground: '#5aa1c5'
      }
    },
    {
      scope: ['entity.name.tag', 'meta.tag', 'support.type.property-name'],
      settings: {
        foreground: '#c06190'
      }
    },
    {
      scope: ['variable.language', 'variable.parameter', 'entity.other.attribute-name'],
      settings: {
        foreground: '#b0703d'
      }
    }
  ]
}

export const darkTheme: ThemeRegistration = {
  name: 'ido-dark',
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
        foreground: '#7d859e',
        fontStyle: 'italic'
      }
    },
    {
      scope: ['keyword', 'storage.type', 'storage.modifier', 'keyword.control', 'keyword.other'],
      settings: {
        foreground: '#a7b0ff',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['string', 'string.quoted', 'string.template'],
      settings: {
        foreground: '#9ad0b0'
      }
    },
    {
      scope: ['entity.name.function', 'support.function', 'meta.function-call'],
      settings: {
        foreground: '#a6c0ff',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['constant.numeric', 'constant.language', 'constant.other'],
      settings: {
        foreground: '#f5c09e'
      }
    },
    {
      scope: ['variable', 'support.variable', 'variable.other'],
      settings: {
        foreground: '#cbd4ff'
      }
    },
    {
      scope: ['entity.name.type', 'support.type', 'support.class', 'support.interface'],
      settings: {
        foreground: '#a7dcff',
        fontStyle: 'bold'
      }
    },
    {
      scope: ['punctuation', 'meta.brace', 'keyword.operator'],
      settings: {
        foreground: '#a7dcff'
      }
    },
    {
      scope: ['entity.name.tag', 'meta.tag', 'support.type.property-name'],
      settings: {
        foreground: '#f6b1ba'
      }
    },
    {
      scope: ['variable.language', 'variable.parameter', 'entity.other.attribute-name'],
      settings: {
        foreground: '#f8dcb7'
      }
    }
  ]
}
