// Run with: node frontend/src/i18n/i18n.test.mjs
import assert from 'node:assert/strict'
import { t, setLang, getLang, registerCatalogs } from './index.js'

registerCatalogs(
  { 'a.b': 'Hello', greet: 'Hi {name}' },   // en
  { 'a.b': 'Xin chào', greet: 'Chào {name}' }, // vi
)

// default language is en
setLang('en')
assert.equal(getLang(), 'en')
assert.equal(t('a.b'), 'Hello')

// switch to vi
setLang('vi')
assert.equal(t('a.b'), 'Xin chào')

// missing key → fallback arg, then key
assert.equal(t('missing.key', 'FB'), 'FB')
assert.equal(t('missing.key'), 'missing.key')

// interpolation
assert.equal(t('greet', undefined, { name: 'An' }), 'Chào An')
// missing param left literal
assert.equal(t('greet'), 'Chào {name}')

console.log('OK i18n core')
