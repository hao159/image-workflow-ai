// Run with: node frontend/src/node-params-reconcile.test.mjs
import assert from 'node:assert/strict'
import { reconcileParams } from './node-params-reconcile.js'

// Bug chính: node tạo lúc chưa có cấu hình (provider="") → sau khi thêm cấu hình,
// options có giá trị mới → reconcile phải gán provider về default mới.
const metaWithConfig = {
  params: [{ name: 'provider', ptype: 'select', default: 'My Config', options: ['My Config'] }],
}
assert.deepEqual(
  reconcileParams({ provider: '' }, metaWithConfig),
  { provider: 'My Config' },
)

// Giá trị trỏ tới cấu hình đã bị xoá/đổi tên → snap về options[0].
assert.deepEqual(
  reconcileParams({ provider: 'Deleted Config' }, metaWithConfig),
  { provider: 'My Config' },
)

// Giá trị còn hợp lệ → giữ nguyên, trả về CÙNG tham chiếu (không re-render thừa).
const valid = { provider: 'My Config' }
assert.equal(reconcileParams(valid, metaWithConfig), valid)

// Chưa có cấu hình nào (options rỗng) → không đổi, giữ "" để chờ cấu hình.
const empty = { provider: '' }
assert.equal(
  reconcileParams(empty, { params: [{ name: 'provider', ptype: 'select', default: '', options: [] }] }),
  empty,
)

// default không nằm trong options → fallback options[0].
assert.deepEqual(
  reconcileParams({ provider: '' }, {
    params: [{ name: 'provider', ptype: 'select', default: 'Stale Default', options: ['A', 'B'] }],
  }),
  { provider: 'A' },
)

// Param select TĨNH (vd filter mode) có giá trị hợp lệ → không bị động vào.
const staticSel = { mode: 'blur' }
assert.equal(
  reconcileParams(staticSel, {
    params: [{ name: 'mode', ptype: 'select', default: 'grayscale', options: ['grayscale', 'blur'] }],
  }),
  staticSel,
)

// Param không phải select → bỏ qua hoàn toàn.
const textParam = { prompt: '' }
assert.equal(
  reconcileParams(textParam, { params: [{ name: 'prompt', ptype: 'textarea', default: '' }] }),
  textParam,
)

// Nhiều select cùng lúc: chỉ cái không hợp lệ bị sửa.
assert.deepEqual(
  reconcileParams({ provider: '', mode: 'blur' }, {
    params: [
      { name: 'provider', ptype: 'select', default: 'Cfg', options: ['Cfg'] },
      { name: 'mode', ptype: 'select', default: 'grayscale', options: ['grayscale', 'blur'] },
    ],
  }),
  { provider: 'Cfg', mode: 'blur' },
)

// meta thiếu/không hợp lệ → trả về params nguyên trạng (hoặc {} khi undefined).
assert.deepEqual(reconcileParams({ a: 1 }, null), { a: 1 })
assert.deepEqual(reconcileParams(undefined, { params: [] }), {})
// params undefined + meta có select → coi như {} rồi reconcile bình thường.
assert.deepEqual(reconcileParams(undefined, metaWithConfig), { provider: 'My Config' })

console.log('node-params-reconcile.test.mjs: all assertions passed')
