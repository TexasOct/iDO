import React from 'react'
import ReactDOM from 'react-dom/client'
import '@/styles/index.css'
import '@/lib/i18n'

import Live2DApp from './App'

ReactDOM.createRoot(document.getElementById('live2d-root') as HTMLElement).render(
  <React.StrictMode>
    <Live2DApp />
  </React.StrictMode>
)
