// Run with: node frontend/src/i18n/error-i18n.test.mjs
import assert from 'node:assert/strict'
import { registerCatalogs, translateError, setLang } from './index.js'

const enCat = {
  'error.generic': 'Something went wrong.',
  'error.workflow_not_found': 'Workflow not found.',
  'error.region_not_found': 'Could not find the object in the image. Try a different description.',
}
const viCat = {
  'error.generic': 'Đã xảy ra lỗi.',
  'error.workflow_not_found': 'Không tìm thấy workflow.',
  'error.region_not_found': 'Không tìm thấy đối tượng trong ảnh. Thử mô tả khác.',
}

registerCatalogs(enCat, viCat)
setLang('en')

// Known code → catalog value (EN)
assert.equal(
  translateError('workflow_not_found', 'fallback'),
  'Workflow not found.',
  'known code should return EN catalog value',
)

// null/undefined code → fallbackMessage
assert.equal(
  translateError(null, 'raw'),
  'raw',
  'null code should return fallback string',
)
assert.equal(
  translateError(undefined, 'raw msg'),
  'raw msg',
  'undefined code should return fallback string',
)

// Unknown code → fallback (code not in catalog, t() returns fallback)
assert.equal(
  translateError('unknown_code', 'raw msg'),
  'raw msg',
  'unknown code should fall back to raw message',
)

// No code, no fallback → generic
assert.equal(
  translateError(null, undefined),
  'Something went wrong.',
  'null code + no fallback should return error.generic',
)

// Switch to VI → catalog in VI
setLang('vi')
assert.equal(
  translateError('workflow_not_found', 'fallback'),
  'Không tìm thấy workflow.',
  'known code should return VI catalog value when lang=vi',
)

// VI + unknown code → fallback (not in catalog)
assert.equal(
  translateError('unknown_code', 'raw vi msg'),
  'raw vi msg',
  'unknown code in vi should fall back to raw message',
)

// VI + null code + no fallback → vi generic
assert.equal(
  translateError(null, undefined),
  'Đã xảy ra lỗi.',
  'null code + no fallback in vi should return vi error.generic',
)

console.log('OK error-i18n')
