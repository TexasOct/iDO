import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { router } from '@/routes/Index'

// Disable refresh and DevTools shortcuts in production
if (import.meta.env.PROD) {
  window.addEventListener('keydown', (e) => {
    // Prevent F5, Ctrl+R, Cmd+R (refresh)
    if (e.key === 'F5' || ((e.ctrlKey || e.metaKey) && e.key === 'r')) {
      e.preventDefault()
      return false
    }
    // Prevent F12, Ctrl+Shift+I, Cmd+Option+I (DevTools)
    if (
      e.key === 'F12' ||
      ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'I') ||
      ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'i')
    ) {
      e.preventDefault()
      return false
    }
    // Prevent Ctrl+Shift+C, Cmd+Option+C (DevTools element picker)
    if (
      ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'C') ||
      ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'c')
    ) {
      e.preventDefault()
      return false
    }
  })

  // Disable right-click context menu in production
  window.addEventListener('contextmenu', (e) => {
    e.preventDefault()
    return false
  })
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(<RouterProvider router={router} />)
