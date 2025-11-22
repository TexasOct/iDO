import { defineConfig } from 'vite'
import path from 'path'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import AutoImport from 'unplugin-auto-import/vite'

const host = '127.0.0.1'

// https://vitejs.dev/config/
export default defineConfig({
  // Suppress the esbuildOptions deprecation warning from @tailwindcss/vite
  // This plugin sets esbuildOptions internally, but Vite 7+ uses Rolldown instead
  // This is a known issue and can be safely ignored for now
  // Reference: https://github.com/tailwindlabs/tailwindcss/discussions/15012
  plugins: [
    react(),
    tailwindcss(),
    AutoImport({
      imports: ['react', 'react-router'],
      dts: './src/types/auto-imports.d.ts',
      dirs: ['src/layouts', 'src/views'],
      eslintrc: {
        enabled: true
      },
      defaultExportByFilename: true
    })
  ],

  // Dependency optimization - explicitly prebundle these deps
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router',
      'react-router-dom',
      'zustand',
      'zustand/middleware',
      'react-i18next',
      'i18next',
      'sonner',
      'next-themes'
    ],
    // Use rollupOptions for Vite 7+ with Rolldown instead of deprecated esbuildOptions
    rollupOptions: {
      // Configuration for dependency optimization with Rolldown
    }
  },

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: 'ws',
          host,
          port: 1421
        }
      : undefined,
    watch: {
      // 3. tell vite to ignore watching `src-tauri`
      ignored: ['**/src-tauri/**', '**/.venv/**', '**/*.md', '**/backend/**']
    },
    middlewareMode: false
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },

  // Build configuration
  build: {
    sourcemap: false,
    reportCompressedSize: false,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
        live2d: path.resolve(__dirname, 'live2d.html')
      },
      output: {
        manualChunks: (id) => {
          // Vendor chunks for better caching
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'vendor-react'
          }
          if (id.includes('node_modules/react-router')) {
            return 'vendor-router'
          }
          if (id.includes('node_modules/sonner') || id.includes('node_modules/next-themes')) {
            return 'vendor-ui'
          }
        }
      }
    }
  }
})
