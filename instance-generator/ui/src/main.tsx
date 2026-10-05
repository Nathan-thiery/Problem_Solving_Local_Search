import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error("L'élément racine #root n'a pas été trouvé dans le document HTML.")
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)