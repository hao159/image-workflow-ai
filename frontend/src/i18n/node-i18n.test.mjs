// Run with: node frontend/src/i18n/node-i18n.test.mjs
import assert from 'node:assert/strict'
import { registerCatalogs, setLang } from './index.js'
import { nodeTitle, nodeCategory, paramLabel } from './node-i18n.js'

registerCatalogs(
  { 'nodes.edit_image.title': 'Edit image (AI)', 'category.ai': 'AI',
    'nodes.edit_image.params.prompt.label': 'Edit prompt' },
  {},
)
setLang('en')
assert.equal(nodeTitle({ type: 'edit_image', title: 'Sửa ảnh (AI)' }), 'Edit image (AI)')
assert.equal(paramLabel('edit_image', { name: 'prompt', label: 'X' }), 'Edit prompt')
assert.equal(nodeCategory('AI'), 'AI')

// vi mode falls back to backend strings (catalog empty)
setLang('vi')
assert.equal(nodeTitle({ type: 'edit_image', title: 'Sửa ảnh (AI)' }), 'Sửa ảnh (AI)')
assert.equal(nodeCategory('Đầu vào'), 'Đầu vào')
console.log('OK node-i18n')
