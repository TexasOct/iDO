/**
 * System Tray Hook
 *
 * Manages the system tray icon and menu with i18n support.
 * Uses Tauri's TrayIcon API from JavaScript.
 */

import { useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { TrayIcon } from '@tauri-apps/api/tray'
import { defaultWindowIcon } from '@tauri-apps/api/app'
import { Menu, MenuItem, PredefinedMenuItem } from '@tauri-apps/api/menu'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { WebviewWindow } from '@tauri-apps/api/webviewWindow'
import { isTauri } from '@/lib/utils/tauri'
import type { UnlistenFn } from '@tauri-apps/api/event'
import { emit } from '@tauri-apps/api/event'

export function useTray() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const trayRef = useRef<TrayIcon | null>(null)
  const isInitializedRef = useRef(false)

  // Create menu function that can be reused
  const createMenu = useCallback(async () => {
    console.log('[Tray] Creating menu with current language:', i18n.language)

    // Create menu items with i18n translations
    const showItem = await MenuItem.new({
      id: 'show',
      text: t('tray.show'),
      action: async () => {
        const window = getCurrentWindow()
        await window.unminimize()
        await window.show()
        await window.setFocus()
      }
    })

    const hideItem = await MenuItem.new({
      id: 'hide',
      text: t('tray.hide'),
      action: async () => {
        const window = getCurrentWindow()
        await window.hide()
      }
    })

    const separator1 = await PredefinedMenuItem.new({ item: 'Separator' })

    // Navigation items
    const dashboardItem = await MenuItem.new({
      id: 'dashboard',
      text: t('tray.dashboard'),
      action: async () => {
        const window = getCurrentWindow()
        await window.unminimize()
        await window.show()
        await window.setFocus()
        navigate('/dashboard')
      }
    })

    const activityItem = await MenuItem.new({
      id: 'activity',
      text: t('tray.activity'),
      action: async () => {
        const window = getCurrentWindow()
        await window.unminimize()
        await window.show()
        await window.setFocus()
        navigate('/activity')
      }
    })

    const chatItem = await MenuItem.new({
      id: 'chat',
      text: t('tray.chat'),
      action: async () => {
        const window = getCurrentWindow()
        await window.unminimize()
        await window.show()
        await window.setFocus()
        navigate('/chat')
      }
    })

    const agentsItem = await MenuItem.new({
      id: 'agents',
      text: t('tray.agents'),
      action: async () => {
        const window = getCurrentWindow()
        await window.unminimize()
        await window.show()
        await window.setFocus()
        navigate('/agents')
      }
    })

    const settingsItem = await MenuItem.new({
      id: 'settings',
      text: t('tray.settings'),
      action: async () => {
        const window = getCurrentWindow()
        await window.unminimize()
        await window.show()
        await window.setFocus()
        navigate('/settings')
      }
    })

    const separator2 = await PredefinedMenuItem.new({ item: 'Separator' })

    const aboutItem = await MenuItem.new({
      id: 'about',
      text: t('tray.about'),
      action: async () => {
        try {
          // Try to get existing about window
          const aboutWindow = await WebviewWindow.getByLabel('about')

          if (aboutWindow) {
            // Window exists, just show and focus it
            await aboutWindow.show()
            await aboutWindow.unminimize()
            await aboutWindow.setFocus()
          } else {
            // Window doesn't exist, create new one
            // Disable decorations on all platforms to avoid duplicate window controls
            // All platforms will use the custom titlebar from About.tsx
            const newAboutWindow = new WebviewWindow('about', {
              url: '/about',
              title: 'About iDO',
              width: 400,
              height: 500,
              fullscreen: false,
              resizable: false,
              center: true,
              skipTaskbar: true,
              transparent: true, // Make window transparent to fully hide system decorations
              decorations: false, // Disable window decorations (titlebar, buttons)
              hiddenTitle: true // Hide title in taskbar
            })

            // Wait for window to be ready
            await newAboutWindow.once('tauri://created', () => {
              console.log('[Tray] About window created')
            })

            await newAboutWindow.once('tauri://error', (e) => {
              console.error('[Tray] About window creation error:', e)
            })
          }
        } catch (error) {
          console.error('[Tray] Failed to open About window:', error)
        }
      }
    })

    const separator3 = await PredefinedMenuItem.new({ item: 'Separator' })

    const quitItem = await MenuItem.new({
      id: 'quit',
      text: t('tray.quit'),
      action: async () => {
        // Show window first (if hidden)
        const window = getCurrentWindow()
        await window.unminimize()
        await window.show()
        await window.setFocus()

        // Emit event to show quit confirmation dialog in the frontend
        console.log('[Tray] Emitting quit-requested event')
        await emit('quit-requested')
      }
    })

    // Create and return menu
    return await Menu.new({
      items: [
        showItem,
        hideItem,
        separator1,
        dashboardItem,
        activityItem,
        chatItem,
        agentsItem,
        settingsItem,
        separator2,
        aboutItem,
        separator3,
        quitItem
      ]
    })
  }, [t, i18n.language, navigate])

  // Initialize tray only once
  useEffect(() => {
    // Only initialize tray in Tauri environment
    if (!isTauri()) {
      console.log('[Tray] Not in Tauri environment, skipping initialization')
      return
    }

    // Only initialize in main window, not in other windows like about
    const checkWindow = async () => {
      const currentWindow = getCurrentWindow()
      const label = currentWindow.label
      if (label !== 'main' && label !== 'iDO') {
        console.log(`[Tray] Skipping initialization in window: ${label}`)
        return false
      }
      return true
    }

    // Prevent multiple initializations
    if (isInitializedRef.current) {
      console.log('[Tray] Already initialized, skipping')
      return
    }

    let mounted = true
    let tray: TrayIcon | null = null
    let unlistenCloseRequested: UnlistenFn | null = null
    let unlistenWillExit: UnlistenFn | null = null

    const initTray = async () => {
      // Check if we should initialize in this window
      const shouldInit = await checkWindow()
      if (!shouldInit) {
        return
      }

      try {
        console.log('[Tray] Initializing system tray...')

        // Create initial menu
        const menu = await createMenu()

        // Create tray icon
        const icon = await defaultWindowIcon()
        tray = await TrayIcon.new({
          icon: icon ?? undefined,
          menu,
          menuOnLeftClick: false, // Show menu only on right-click
          tooltip: 'iDO - AI Activity Monitor',
          action: async (event) => {
            // Left click: show and focus window
            if (event.type === 'Click' && event.button === 'Left' && event.buttonState === 'Up') {
              const window = getCurrentWindow()
              await window.unminimize()
              await window.show()
              await window.setFocus()
            }
          }
        })

        if (mounted) {
          trayRef.current = tray
          isInitializedRef.current = true
          console.log('[Tray] System tray initialized successfully')
        }

        // Intercept window close event to hide instead of exit
        const window = getCurrentWindow()
        unlistenCloseRequested = await window.onCloseRequested(async (event) => {
          // Prevent the default close behavior
          event.preventDefault()

          // Hide the window instead
          await window.hide()
          console.log('[Tray] Window hidden instead of closed')
        })

        if (mounted) {
          console.log('[Tray] Window close handler registered')
        }

        // Listen for app-will-exit event to cleanup tray before exit
        const { listen: listenToEvent } = await import('@tauri-apps/api/event')
        unlistenWillExit = await listenToEvent('app-will-exit', async () => {
          console.log('[Tray] Received app-will-exit, cleaning up tray')
          try {
            // Try to remove tray icon before exit
            if (tray) {
              // Note: Tauri 2.x doesn't have explicit remove method
              // The tray will be cleaned up automatically, but we null the reference
              tray = null
              trayRef.current = null
              console.log('[Tray] Tray reference cleared')
            }
          } catch (cleanupError) {
            console.error('[Tray] Error cleaning up tray:', cleanupError)
          }
        })
      } catch (error) {
        console.error('[Tray] Failed to initialize system tray:', error)
      }
    }

    // Initialize tray
    void initTray()

    // Cleanup
    return () => {
      mounted = false
      // Cleanup event listeners
      if (unlistenCloseRequested) {
        unlistenCloseRequested()
      }
      if (unlistenWillExit) {
        unlistenWillExit()
      }
      // Clear tray reference
      tray = null
      trayRef.current = null
      isInitializedRef.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Initialize only once on mount

  // Update tray menu when language changes
  useEffect(() => {
    // Only update if tray is already initialized
    if (!isInitializedRef.current || !trayRef.current) {
      return
    }

    const updateTrayMenu = async () => {
      try {
        console.log('[Tray] Language changed, updating menu...')
        const newMenu = await createMenu()
        await trayRef.current?.setMenu(newMenu)
        console.log('[Tray] Menu updated successfully')
      } catch (error) {
        console.error('[Tray] Failed to update tray menu:', error)
      }
    }

    void updateTrayMenu()
  }, [i18n.language, createMenu])

  return trayRef
}
