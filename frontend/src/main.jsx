import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import CreateUpgradeTreeForm from './upgradeTreeForm'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <CreateUpgradeTreeForm />
  </StrictMode>,
)
