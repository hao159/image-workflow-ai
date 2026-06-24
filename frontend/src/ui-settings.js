// Setting giao diện phía client, lưu localStorage (không cần backend).
// Hiện có: theme sáng/tối, hiệu ứng hiển thị khi node đang chạy.
import { categoryStyle } from './node-category-styles.js'
import { t } from './i18n/index.js'

const STORAGE_KEY = 'iw-ui-settings'

// Getter functions so labels re-evaluate at call time → live language switch.
export function getRunEffectOptions() {
  return [
    { value: 'solid', label: t('settings.runEffect.solid') },
    { value: 'auto',  label: t('settings.runEffect.auto') },
    { value: 'glow',  label: t('settings.runEffect.glow') },
    { value: 'scan',  label: t('settings.runEffect.scan') },
    { value: 'pulse', label: t('settings.runEffect.pulse') },
    { value: 'off',   label: t('settings.runEffect.off') },
  ]
}

// Theme: 'system' bám prefers-color-scheme của OS; 'light'/'dark' ép cứng.
export function getThemeOptions() {
  return [
    { value: 'system', label: t('settings.theme.system') },
    { value: 'light',  label: t('settings.theme.light') },
    { value: 'dark',   label: t('settings.theme.dark') },
  ]
}

let cached = null
let themeCached = null

function readSettings() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
  } catch {
    return {}
  }
}

export function getRunEffect() {
  if (cached === null) cached = readSettings().runEffect || 'solid'
  return cached
}

export function setRunEffect(value) {
  cached = value
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...readSettings(), runEffect: value }))
}

// Trả về tên hiệu ứng áp cho node đang chạy (null = không hiệu ứng).
// 'auto' → mỗi loại node một hiệu ứng riêng theo CATEGORY_STYLES.
export function resolveRunEffect(category) {
  const setting = getRunEffect()
  if (setting === 'off') return null
  if (setting !== 'auto') return setting
  return categoryStyle(category).runEffect
}

/* ---------- Theme sáng/tối ---------- */

const THEME_EVENT = 'iw-theme-change'

export function getThemeSetting() {
  if (themeCached === null) themeCached = readSettings().theme || 'system'
  return themeCached
}

const prefersDark = () =>
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-color-scheme: dark)').matches

// Theme thực tế đang hiển thị: 'light' | 'dark'. 'system' → theo OS.
export function resolveTheme() {
  const setting = getThemeSetting()
  if (setting === 'light' || setting === 'dark') return setting
  return prefersDark() ? 'dark' : 'light'
}

// Áp theme lên <html data-theme=...> + phát sự kiện cho component cần biết
// (vd React Flow colorMode). Gọi TRƯỚC render lần đầu để tránh nhấp nháy (FOUC).
export function applyTheme() {
  const theme = resolveTheme()
  document.documentElement.setAttribute('data-theme', theme)
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(THEME_EVENT, { detail: { theme } }))
  }
  return theme
}

export function setThemeSetting(value) {
  themeCached = value
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...readSettings(), theme: value }))
  applyTheme()
}

// Theo dõi OS đổi theme — chỉ áp lại khi đang ở chế độ 'system'. Gọi 1 lần lúc khởi động.
export function initThemeWatcher() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
  window
    .matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => {
      if (getThemeSetting() === 'system') applyTheme()
    })
}
