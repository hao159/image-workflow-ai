import { useI18nContext } from './i18n-provider.jsx'

// Components call useT() so they re-render when language changes.
export function useT() {
  return useI18nContext()
}
