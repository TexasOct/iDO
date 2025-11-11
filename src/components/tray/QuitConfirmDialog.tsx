/**
 * Quit Confirmation Dialog
 *
 * Shows a confirmation dialog when user tries to quit the application
 */

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listen } from '@tauri-apps/api/event'
import { emit } from '@tauri-apps/api/event'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'

export function QuitConfirmDialog() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let unlisten: (() => void) | undefined

    // Listen for quit-requested event from tray
    listen('quit-requested', () => {
      console.log('[QuitConfirmDialog] Quit requested, showing dialog')
      setOpen(true)
    }).then((unlistenFn) => {
      unlisten = unlistenFn
    })

    return () => {
      if (unlisten) {
        unlisten()
      }
    }
  }, [])

  const handleConfirm = async () => {
    console.log('[QuitConfirmDialog] User confirmed exit')
    setOpen(false)
    // Emit app-exit event to trigger backend cleanup
    await emit('app-exit')
  }

  const handleCancel = () => {
    console.log('[QuitConfirmDialog] User cancelled exit')
    setOpen(false)
  }

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t('tray.quitConfirmTitle')}</AlertDialogTitle>
          <AlertDialogDescription>{t('tray.quitConfirmMessage')}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel}>{t('tray.quitConfirmCancel')}</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm}>{t('tray.quitConfirmOk')}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
