import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { router } from '@/routes/Index'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(<RouterProvider router={router} />)
