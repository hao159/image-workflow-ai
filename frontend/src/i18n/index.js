// Lightweight i18n: module-level current language so t() works everywhere
// (React components AND plain modules like api.js). I18nProvider handles re-render.
// Catalogs are installed via registerCatalogs() (see load-catalogs.js) rather than
// imported here, so the .mjs tests run under bare node without JSON import attributes.
const STORAGE_KEY = 'iw-ui-settings'
export const LANG_EVENT = 'iw-lang-change'
const SUPPORTED = ['en', 'vi']
const DEFAULT_LANG = 'en'

export const LANG_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'vi', label: 'Tiếng Việt' },
]

let catalogs = { en: {}, vi: {} }
let current = null

function readSettings() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
  } catch {
    return {}
  }
}

export function getLang() {
  if (current === null) {
    const stored = readSettings().lang
    current = SUPPORTED.includes(stored) ? stored : DEFAULT_LANG
  }
  return current
}

export function setLang(lang) {
  if (!SUPPORTED.includes(lang)) return
  current = lang
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...readSettings(), lang }))
  } catch {
    /* localStorage unavailable — keep in-memory only */
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(LANG_EVENT, { detail: { lang } }))
  }
}

// Resolve key in active catalog. Missing → fallback string (if provided) else key.
// Interpolates {var} from params.
export function t(key, fallback, params) {
  const lang = getLang()
  const raw = catalogs[lang]?.[key] ?? (typeof fallback === 'string' ? fallback : key)
  if (!params) return raw
  return raw.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m))
}

// Install catalogs. App calls this once via load-catalogs.js with the bundled
// JSON; tests call it with inline objects.
export function registerCatalogs(enCat, viCat) {
  catalogs = { en: enCat || {}, vi: viCat || {} }
}

// Translate a backend error by code, falling back to the raw backend message.
// If no code is provided, returns fallbackMessage (or generic error string).
// Supports {var} interpolation via params.
export function translateError(code, fallbackMessage, params) {
  if (!code) return fallbackMessage || t('error.generic')
  return t(`error.${code}`, fallbackMessage, params)
}
