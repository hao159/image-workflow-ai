import React from 'react'
import ReactDOM from 'react-dom/client'
import { ReactFlowProvider } from '@xyflow/react'
import './i18n/load-catalogs.js'
import { I18nProvider } from './i18n/i18n-provider.jsx'
import App from './App.jsx'
import { ToastProvider } from './ToastContext.jsx'
import { applyTheme, initThemeWatcher } from './ui-settings.js'
import '@xyflow/react/dist/style.css'
import './styles.css'

// Áp theme TRƯỚC khi React render để tránh nhấp nháy theme cũ (FOUC),
// rồi theo dõi OS đổi theme khi đang ở chế độ 'system'.
applyTheme()
initThemeWatcher()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <I18nProvider>
      <ReactFlowProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </ReactFlowProvider>
    </I18nProvider>
  </React.StrictMode>,
)
