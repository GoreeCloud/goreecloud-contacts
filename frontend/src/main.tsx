import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import './styles.css'
import './glaze.css'
import './glaze-accessibility.css'
import './glaze-form-factors.css'
import './glaze-form-factor-refinements.css'
import './glaze-v1.1.css'

const root = document.getElementById('root')

if (!root) {
  throw new Error('Root element was not found.')
}

createRoot(root).render(
  <StrictMode>
    <a className="skip-link" href="#contacts">
      Skip to contacts
    </a>
    <App />
  </StrictMode>,
)
