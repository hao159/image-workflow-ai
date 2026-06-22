import { createContext, useContext, useEffect, useState } from 'react'
import { getLang, setLang as setLangModule, t, LANG_EVENT } from './index.js'

const I18nContext = createContext(null)

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(getLang)

  useEffect(() => {
    const onChange = (e) => setLangState(e.detail?.lang ?? getLang())
    window.addEventListener(LANG_EVENT, onChange)
    return () => window.removeEventListener(LANG_EVENT, onChange)
  }, [])

  return (
    <I18nContext.Provider value={{ t, lang, setLang: setLangModule }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18nContext() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useT must be used inside <I18nProvider>')
  return ctx
}
