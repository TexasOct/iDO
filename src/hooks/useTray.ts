/**
 * System Tray Hook
 *
 * Manages the system tray icon and menu with i18n support.
 * Uses Tauri's TrayIcon API from JavaScript.
 */

import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { TrayIcon } from '@tauri-apps/api/tray'
import { defaultWindowIcon } from '@tauri-apps/api/app'
import { Menu, MenuItem, PredefinedMenuItem } from '@tauri-apps/api/menu'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { isTauri } from '@/lib/utils/tauri'
import type { UnlistenFn } from '@tauri-apps/api/event'
import { emit } from '@tauri-apps/api/event'

export function useTray() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const trayRef = useRef<TrayIcon | null>(null)
  const currentLanguage = i18n.language

  useEffect(() => {
    // Only initialize tray in Tauri environment
    if (!isTauri()) {
      console.log('[Tray] Not in Tauri environment, skipping initialization')
      return
    }
    let mounted = true
    let tray: TrayIcon | null = null
    let unlistenCloseRequested: UnlistenFn | null = null
    let unlistenWillExit: UnlistenFn | null = null

    const initTray = async () => {
      try {
        // Add a small delay to ensure i18n is fully loaded
        await new Promise((resolve) => setTimeout(resolve, 500))

        console.log('[Tray] Initializing with language:', currentLanguage)
        console.log('[Tray] i18n initialized:', i18n.isInitialized)
        console.log('[Tray] Available languages:', Object.keys(i18n.services.resourceStore.data))
        console.log('[Tray] Show text:', t('tray.show'))
        console.log('[Tray] Hide text:', t('tray.hide'))
        console.log('[Tray] Dashboard text:', t('tray.dashboard'))

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
            const window = getCurrentWindow()
            await window.unminimize()
            await window.show()
            await window.setFocus()
            // Could emit an event to show about dialog
            console.log('About iDO clicked')
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

        // Create menu
        const menu = await Menu.new({
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
    }
  }, [t, navigate, currentLanguage]) // Re-initialize when language changes

  return trayRef
}
