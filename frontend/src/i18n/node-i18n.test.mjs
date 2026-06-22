// Run with: node frontend/src/i18n/node-i18n.test.mjs
import assert from 'node:assert/strict'
import { registerCatalogs, setLang } from './index.js'
import { nodeTitle, nodeCategory, paramLabel, portLabel } from './node-i18n.js'

registerCatalogs(
  { 'nodes.edit_image.title': 'Edit image (AI)', 'category.ai': 'AI',
    'nodes.edit_image.params.prompt.label': 'Edit prompt',
    'nodes.enhance_prompt.inputs.text': 'Base prompt',
    'nodes.enhance_prompt.outputs.text': 'Enhanced prompt' },
  {},
)
setLang('en')
assert.equal(nodeTitle({ type: 'edit_image', title: 'Sửa ảnh (AI)' }), 'Edit image (AI)')
assert.equal(paramLabel('edit_image', { name: 'prompt', label: 'X' }), 'Edit prompt')
assert.equal(nodeCategory('AI'), 'AI')

// directional port keys: same port name resolves differently per direction
assert.equal(portLabel('enhance_prompt', { name: 'text', label: 'X' }, 'inputs'), 'Base prompt')
assert.equal(portLabel('enhance_prompt', { name: 'text', label: 'X' }, 'outputs'), 'Enhanced prompt')
// fallback to port.label when no catalog key
assert.equal(portLabel('enhance_prompt', { name: 'text', label: 'Fallback' }, 'inputs'), 'Base prompt')
assert.equal(portLabel('unknown_node', { name: 'text', label: 'Fallback' }, 'outputs'), 'Fallback')

// vi mode falls back to backend strings (catalog empty)
setLang('vi')
assert.equal(nodeTitle({ type: 'edit_image', title: 'Sửa ảnh (AI)' }), 'Sửa ảnh (AI)')
assert.equal(nodeCategory('Đầu vào'), 'Đầu vào')
console.log('OK node-i18n')
