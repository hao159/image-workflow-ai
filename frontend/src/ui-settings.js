// Setting giao diện phía client, lưu localStorage (không cần backend).
// Hiện có: hiệu ứng hiển thị khi node đang chạy.
import { categoryStyle } from './node-category-styles.js'

const STORAGE_KEY = 'iw-ui-settings'

export const RUN_EFFECT_OPTIONS = [
  { value: 'auto', label: 'Theo loại node (mặc định)' },
  { value: 'glow', label: 'Viền phát sáng' },
  { value: 'scan', label: 'Thanh quét dưới header' },
  { value: 'pulse', label: 'Nhịp đập viền' },
  { value: 'off', label: 'Tắt hiệu ứng' },
]

let cached = null

function readSettings() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
  } catch {
    return {}
  }
}

export function getRunEffect() {
  if (cached === null) cached = readSettings().runEffect || 'auto'
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
