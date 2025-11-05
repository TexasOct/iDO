import React from 'react'
import ReactDOM from 'react-dom/client'

import Live2DApp from './App'

ReactDOM.createRoot(document.getElementById('live2d-root') as HTMLElement).render(
  <React.StrictMode>
    <Live2DApp />
  </React.StrictMode>
)
