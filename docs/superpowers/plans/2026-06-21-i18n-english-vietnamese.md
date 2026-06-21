# i18n (English + Vietnamese) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Image Workflow app bilingual (English default, Vietnamese secondary) covering frontend UI, backend node-schema strings, and backend error messages, plus a bilingual README.

**Architecture:** A lightweight custom i18n layer in the frontend (no new dependency). A module-level `t()` reads the current language so it works in React and non-React code; an `I18nProvider` re-renders the tree on language change. Backend node schema is left untranslated and overlaid in the frontend by stable IDs (`type`/param `name`/port `name`); backend errors gain a stable `code` (+ optional `params`) that the frontend translates, falling back to the raw backend text.

**Tech Stack:** React 18 + Vite (plain JSX), Python + FastAPI, JSON catalogs.

## Global Constraints

- No new frontend dependencies — implement i18n by hand (project keeps deps minimal).
- Default language is `en` when no stored preference exists.
- Persist language in the existing `iw-ui-settings` localStorage object (same pattern as theme).
- Vietnamese is the in-code source language; English is authored in catalogs.
- DRY: `vi.json` omits node-schema keys → frontend falls back to the backend Vietnamese strings. `en.json` carries full node-schema English.
- Error `code`s are stable lowercase snake_case domain slugs (e.g. `generate_no_prompt`). Never reference plan artifacts in code/identifiers.
- File naming kebab-case for new JS files; keep files focused (<200 lines).
- Spec: `docs/superpowers/specs/2026-06-21-i18n-vietnamese-english-design.md`.

---

### Task 1: i18n core module (`t`, lang state, persistence)

**Files:**
- Create: `frontend/src/i18n/index.js`
- Create: `frontend/src/i18n/locales/en.json`
- Create: `frontend/src/i18n/locales/vi.json`
- Test: `frontend/src/i18n/i18n.test.mjs`

**Interfaces:**
- Produces:
  - `getLang(): 'en' | 'vi'`
  - `setLang(lang): void` — writes `iw-ui-settings.lang`, updates module state, dispatches `iw-lang-change` CustomEvent.
  - `t(key: string, fallback?: string, params?: object): string` — resolves `catalog[lang][key]`; if missing, uses `fallback` (if a string) else `key`; interpolates `{var}` from `params`.
  - `LANG_OPTIONS: {value, label}[]`
  - Event name constant `LANG_EVENT = 'iw-lang-change'`.

- [ ] **Step 1: Create empty catalogs**

`frontend/src/i18n/locales/en.json`:
```json
{}
```
`frontend/src/i18n/locales/vi.json`:
```json
{}
```

- [ ] **Step 2: Write the failing test**

`frontend/src/i18n/i18n.test.mjs`:
```js
// Run with: node frontend/src/i18n/i18n.test.mjs
import assert from 'node:assert/strict'
import { t, setLang, getLang, __setCatalogsForTest } from './index.js'

__setCatalogsForTest(
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `node frontend/src/i18n/i18n.test.mjs`
Expected: FAIL — `Cannot find module './index.js'` / export missing.

- [ ] **Step 4: Implement `index.js`**

`frontend/src/i18n/index.js`:
```js
// Lightweight i18n: module-level current language so t() works everywhere
// (React components AND plain modules like api.js). I18nProvider handles re-render.
import en from './locales/en.json'
import vi from './locales/vi.json'

const STORAGE_KEY = 'iw-ui-settings'
export const LANG_EVENT = 'iw-lang-change'
const SUPPORTED = ['en', 'vi']
const DEFAULT_LANG = 'en'

export const LANG_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'vi', label: 'Tiếng Việt' },
]

let catalogs = { en, vi }
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

// Test-only hook to inject catalogs without bundler JSON imports.
export function __setCatalogsForTest(enCat, viCat) {
  catalogs = { en: enCat, vi: viCat }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `node frontend/src/i18n/i18n.test.mjs`
Expected: prints `OK i18n core`, exit 0.

> Note: `localStorage`/`window` are undefined under bare `node`. The test only calls `setLang`/`t` which guard `window`; `localStorage` is wrapped in try/catch — safe.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/i18n/
git commit -m "feat(i18n): add core t() resolver with language persistence"
```

---

### Task 2: I18nProvider + useT hook + app wiring

**Files:**
- Create: `frontend/src/i18n/i18n-provider.jsx`
- Create: `frontend/src/i18n/use-t.js`
- Modify: `frontend/src/main.jsx:15-23`

**Interfaces:**
- Consumes: `getLang`, `setLang`, `t`, `LANG_EVENT` from Task 1.
- Produces:
  - `<I18nProvider>` — context provider that re-renders subtree on `iw-lang-change`.
  - `useT(): { t, lang, setLang }` — `t` is a stable reference to the module `t`; `lang` triggers re-render; `setLang` is the module setter.

- [ ] **Step 1: Implement the provider**

`frontend/src/i18n/i18n-provider.jsx`:
```jsx
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

  const setLang = (next) => setLangModule(next) // event listener updates state

  return (
    <I18nContext.Provider value={{ t, lang, setLang }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18nContext() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useT must be used inside <I18nProvider>')
  return ctx
}
```

`frontend/src/i18n/use-t.js`:
```js
import { useI18nContext } from './i18n-provider.jsx'

// Components call useT() so they re-render when language changes.
export function useT() {
  return useI18nContext()
}
```

- [ ] **Step 2: Wire provider in main.jsx**

Modify `frontend/src/main.jsx` — add import and wrap `<App />` (outermost so all children re-render):
```jsx
import { I18nProvider } from './i18n/i18n-provider.jsx'
// ...
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <I18nProvider>
      <ReactFlowProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </ReactFlowProvider>
    </I18nProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 3: Verify build compiles**

Run: `npm run build --prefix frontend`
Expected: build succeeds (no missing-module / JSX errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/i18n/i18n-provider.jsx frontend/src/i18n/use-t.js frontend/src/main.jsx
git commit -m "feat(i18n): add I18nProvider and useT hook, wire into app root"
```

---

### Task 3: Language selector — Settings tab + toolbar quick toggle

**Files:**
- Modify: `frontend/src/components/settings-appearance-tab.jsx`
- Modify: `frontend/src/App.jsx` (toolbar region ~514-571, near the ⚙ Settings button)
- Modify: `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/vi.json`

**Interfaces:**
- Consumes: `useT()` (Task 2), `LANG_OPTIONS` (Task 1).

- [ ] **Step 1: Add catalog keys for the selector**

Add to `en.json`:
```json
{
  "settings.language": "Language",
  "toolbar.language": "Language"
}
```
Add to `vi.json`:
```json
{
  "settings.language": "Ngôn ngữ",
  "toolbar.language": "Ngôn ngữ"
}
```

- [ ] **Step 2: Add language segmented control to the Appearance tab**

In `settings-appearance-tab.jsx`, import and render a row before the theme row:
```jsx
import { useT } from '../i18n/use-t.js'
import { LANG_OPTIONS } from '../i18n/index.js'
// inside component:
const { t, lang, setLang } = useT()
// ...first row in the returned .settings-section:
<div className="settings-row">
  <span>{t('settings.language')}</span>
  <div className="theme-seg" role="group" aria-label={t('settings.language')}>
    {LANG_OPTIONS.map((o) => (
      <button
        key={o.value}
        type="button"
        className={`theme-seg-btn${lang === o.value ? ' active' : ''}`}
        onClick={() => setLang(o.value)}
      >
        {o.label}
      </button>
    ))}
  </div>
</div>
```

- [ ] **Step 3: Add toolbar quick toggle**

In `App.jsx`, add near the top of the component body:
```jsx
import { useT } from './i18n/use-t.js'
import { LANG_OPTIONS } from './i18n/index.js'
// inside App():
const { lang, setLang } = useT()
```
In the toolbar JSX (beside the ⚙ Settings button), insert a compact toggle:
```jsx
<div className="lang-seg" role="group" aria-label={t('toolbar.language')}>
  {LANG_OPTIONS.map((o) => (
    <button
      key={o.value}
      type="button"
      className={`lang-seg-btn${lang === o.value ? ' active' : ''}`}
      onClick={() => setLang(o.value)}
    >
      {o.value.toUpperCase()}
    </button>
  ))}
</div>
```
> If `t` is not already in scope in `App.jsx`, also pull it from `useT()`.

- [ ] **Step 4: Add minimal toolbar toggle styles**

Append to `frontend/src/styles/toolbar.css`:
```css
.lang-seg { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.lang-seg-btn { padding: 4px 8px; font-size: 12px; background: transparent; border: 0; cursor: pointer; color: var(--text); }
.lang-seg-btn.active { background: var(--bg-raised); font-weight: 600; }
```
> Verify the actual CSS variable names in `frontend/src/styles.css`; reuse whatever the existing toolbar buttons use rather than inventing new ones.

- [ ] **Step 5: Verify build + manual smoke**

Run: `npm run build --prefix frontend`
Expected: success. Manual: `npm run dev --prefix frontend`, open app, toggle EN↔VI from both toolbar and Settings → the language label and segmented controls flip immediately and stay in sync.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/settings-appearance-tab.jsx frontend/src/App.jsx frontend/src/styles/toolbar.css frontend/src/i18n/locales/
git commit -m "feat(i18n): add language selector in settings and toolbar quick toggle"
```

---

### Tasks 4–10: Frontend static-string extraction (one task per area)

Each task below targets one area/file-set. The **procedure is identical** for every area:

1. Read the target file(s); find every user-facing Vietnamese literal (JSX text, `aria-label`/`title`/`placeholder` attrs, button labels, option labels, toast/confirm/alert text). Ignore code comments and CSS.
2. For each literal, add a key under the area namespace to **both** `en.json` (authored English) and `vi.json` (the original Vietnamese verbatim).
3. Replace the literal in code with `t('namespace.key')`, pulling `const { t } = useT()` into the component (or importing `t` from `../i18n/index.js` for non-component modules).
4. For dynamic strings, use interpolation: literal `` `Trang ${p}/${n}` `` → `t('history.page', undefined, { p, n })` with catalog value `"Page {p}/{n}"` (en) / `"Trang {p}/{n}"` (vi).
5. Run `npm run build --prefix frontend` (expect success), then commit.

**Acceptance criteria per task:** no user-facing Vietnamese literal remains in the file(s); in VI mode the UI renders identical text to before; build passes.

**Commit message pattern:** `feat(i18n): localize <area> strings`.

> The key names below are the required namespace + slug for each area. Author English in `en.json`; copy the file's existing Vietnamese into `vi.json` under the same key. Read the file for the exact source text (line numbers from the inventory scan are approximate).

- [ ] **Task 4 — Toolbar & top-level App chrome** (`App.jsx`)
  Namespace `toolbar.*` and `status.*`. Keys: `toolbar.run`, `toolbar.stop`, `toolbar.save`, `toolbar.open`, `toolbar.settings`, `toolbar.clearCache`, `toolbar.newWorkflow`, `toolbar.autoLayout`, `toolbar.history`, plus run-status toasts under `status.*` (e.g. `status.done`="Done"/"Hoàn thành", `status.error`="Error"/"Lỗi", `status.stopped`="Stopped"/"Đã dừng", `status.connError`="Connection error"/"Lỗi kết nối"). Add any other literals found in `App.jsx`.

- [ ] **Task 5 — Palette** (`components/Palette.jsx`)
  Namespace `palette.*`: search placeholder, hint text, empty state. Category labels are handled in Task 11 (node overlay), not here.

- [ ] **Task 6 — Settings shell + model tab** (`components/SettingsModal.jsx`, `components/settings-model-tab.jsx`, `components/model-field.jsx`)
  Namespace `settings.*` and `model.*` (30+ strings: tab titles, provider config labels, capability tags, manual-entry text, buttons). Reuse `settings.language` from Task 3.

- [ ] **Task 7 — Workflow browser modal** (`components/workflow-browser-modal.jsx`)
  Namespace `workflowBrowser.*`: title, buttons, empty state, pagination (`‹ Trước`/`Sau ›`/`Trang {p}/{n}` → interpolated).

- [ ] **Task 8 — Image library modal** (`components/image-library-modal.jsx`)
  Namespace `library.*`: tab labels (uploads/outputs), warnings, delete confirms, pagination.

- [ ] **Task 9 — Execution history panel** (`components/execution-history-panel.jsx`)
  Namespace `history.*`: status labels, durations, pagination, empty state.

- [ ] **Task 10 — Small components** (`components/Toast.jsx`, `components/confirm-dialog.jsx`, `components/ImageViewerModal.jsx`, `components/DeletableEdge.jsx`, `components/NodeParamField.jsx`, `components/ConnectNodeMenu.jsx`, `components/WorkflowNode.jsx`)
  Namespaces: `toast.*` (aria labels), `dialog.*` (confirm/cancel buttons), `imageViewer.*`, `edge.delete`, `nodeParam.*` (upload messages, optional/multi-wire hints like `(tùy chọn)`, `(nhiều dây)`, `✓ đã nối`, cache badge). Node **schema** text (title/description/labels) is NOT here — that is Task 11. Static node-UI chrome (badges, hints) IS here.

> Also move `ui-settings.js` option labels (`RUN_EFFECT_OPTIONS`, `THEME_OPTIONS`) into the catalog: since those modules run outside React, import `t` directly from `../i18n/index.js` and compute labels via `t('settings.runEffect.solid')` etc. Do this within Task 6 (settings) since they render in the Appearance tab. Because `t` is evaluated at call time, ensure these option arrays are built inside render (e.g. a `getRunEffectOptions()` function) rather than as module constants, so they re-translate on language switch.

---

### Task 11: Node-schema overlay (frontend)

**Files:**
- Create: `frontend/src/i18n/node-i18n.js`
- Modify: render sites — `components/Palette.jsx`, `components/WorkflowNode.jsx`, `components/NodeParamField.jsx`, `components/ConnectNodeMenu.jsx`
- Modify: `frontend/src/i18n/locales/en.json` (full `nodes.*` + `category.*`)
- Test: `frontend/src/i18n/node-i18n.test.mjs`

**Interfaces:**
- Consumes: `t` from Task 1.
- Produces helpers:
  - `nodeTitle(meta): string` → `t('nodes.{type}.title', meta.title)`
  - `nodeDescription(meta): string` → `t('nodes.{type}.description', meta.description)`
  - `nodeCategory(catVi): string` → maps Vietnamese category → `t('category.{slug}', catVi)`
  - `portLabel(type, port): string` → `t('nodes.{type}.ports.{port.name}', port.label)`
  - `paramLabel(type, param): string` → `t('nodes.{type}.params.{param.name}.label', param.label)`
  - `paramSupplementLabel(type, param): string` → `t('nodes.{type}.params.{param.name}.supplement', param.supplement_label)`

- [ ] **Step 1: Author the English node + category catalog**

Add to `en.json` (verbatim — this is the full node-schema English; `vi.json` gets NONE of these, falling back to backend Vietnamese):
```json
{
  "category.input": "Input",
  "category.ai": "AI",
  "category.transform": "Transform",
  "category.output": "Output",
  "category.other": "Other",

  "nodes.text_prompt.title": "Prompt",
  "nodes.text_prompt.description": "Enter text/prompt to feed into other nodes.",
  "nodes.text_prompt.ports.text": "Text",
  "nodes.text_prompt.params.text.label": "Content",

  "nodes.load_image.title": "Upload image",
  "nodes.load_image.description": "Upload an image from your machine as workflow input.",
  "nodes.load_image.ports.image": "Image",
  "nodes.load_image.params.file_id.label": "Image",
  "nodes.load_image.params.image_label.label": "Image caption",

  "nodes.combine_text.title": "Merge prompts",
  "nodes.combine_text.description": "Merge multiple text fragments into one (one per line). Connect as many wires as you like.",
  "nodes.combine_text.ports.prompts": "Prompts",
  "nodes.combine_text.ports.text": "Text",

  "nodes.save_image.title": "Save image",
  "nodes.save_image.description": "Save the image to the outputs/ folder and show the result.",
  "nodes.save_image.ports.image": "Image",
  "nodes.save_image.ports.path": "Path",
  "nodes.save_image.params.prefix.label": "File name (prefix)",

  "nodes.generate_image.title": "Generate image (AI)",
  "nodes.generate_image.description": "Generate an image from a prompt. The prompt comes from the input port if connected, otherwise from the prompt typed in the node.",
  "nodes.generate_image.ports.prompt": "Prompt",
  "nodes.generate_image.ports.image": "Image",
  "nodes.generate_image.params.provider.label": "Model / Provider",
  "nodes.generate_image.params.prompt.label": "Prompt",
  "nodes.generate_image.params.prompt.supplement": "Extra prompt",
  "nodes.generate_image.params.aspect_ratio.label": "Aspect ratio",
  "nodes.generate_image.params.image_label.label": "Image caption",

  "nodes.edit_image.title": "Edit image (AI)",
  "nodes.edit_image.description": "Edit/compose an image by prompt: change background, add/remove details, change style... The 'Extra images' port accepts multiple wires — connect as many images as you like.",
  "nodes.edit_image.ports.image": "Source image",
  "nodes.edit_image.ports.images": "Extra images",
  "nodes.edit_image.ports.prompt": "Prompt",
  "nodes.edit_image.params.provider.label": "Model / Provider",
  "nodes.edit_image.params.prompt.label": "Edit prompt",
  "nodes.edit_image.params.prompt.supplement": "Extra prompt",
  "nodes.edit_image.params.instruction.label": "System instruction (optional)",

  "nodes.enhance_prompt.title": "Enhance prompt (AI)",
  "nodes.enhance_prompt.description": "Use AI to rewrite the prompt into a richer, more detailed one, then pass it to the Generate/Edit image node. The base prompt comes from the input port if connected, otherwise from the prompt typed in the node.",
  "nodes.enhance_prompt.ports.prompt": "Base prompt",
  "nodes.enhance_prompt.ports.out": "Enhanced prompt",
  "nodes.enhance_prompt.params.provider.label": "Model / Provider",
  "nodes.enhance_prompt.params.prompt.label": "Base prompt",
  "nodes.enhance_prompt.params.prompt.supplement": "Extra prompt",
  "nodes.enhance_prompt.params.style.label": "Extra guidance (optional)",
  "nodes.enhance_prompt.params.detail.label": "Detail level",

  "nodes.extract_region.title": "Extract region (AI)",
  "nodes.extract_region.description": "Extract/crop an object by description (face/person/clothing/animal...). AI finds the region → crops keeping original pixels. The clearer the description, the more accurate.",
  "nodes.extract_region.ports.image": "Image",
  "nodes.extract_region.ports.target": "Object description",
  "nodes.extract_region.ports.out": "Image",
  "nodes.extract_region.params.provider.label": "Model / Provider (vision)",
  "nodes.extract_region.params.target.label": "Object to extract",
  "nodes.extract_region.params.target.supplement": "Extra description",
  "nodes.extract_region.params.padding.label": "Padding (ratio)",
  "nodes.extract_region.params.image_label.label": "Image caption (names the crop)",

  "nodes.resize.title": "Resize",
  "nodes.resize.description": "Resize the image (keep aspect ratio if selected).",
  "nodes.resize.ports.image": "Image",
  "nodes.resize.ports.out": "Image",
  "nodes.resize.params.width.label": "Width (px)",
  "nodes.resize.params.height.label": "Height (px)",
  "nodes.resize.params.keep_aspect.label": "Keep aspect ratio",

  "nodes.filter.title": "Filter",
  "nodes.filter.description": "Apply a simple filter: grayscale, blur, sharpen...",
  "nodes.filter.ports.image": "Image",
  "nodes.filter.ports.out": "Image",
  "nodes.filter.params.filter.label": "Filter",
  "nodes.filter.params.radius.label": "Blur radius",

  "nodes.adjust.title": "Adjust color",
  "nodes.adjust.description": "Adjust brightness, contrast, color saturation.",
  "nodes.adjust.ports.image": "Image",
  "nodes.adjust.ports.out": "Image",
  "nodes.adjust.params.brightness.label": "Brightness",
  "nodes.adjust.params.contrast.label": "Contrast",
  "nodes.adjust.params.saturation.label": "Saturation"
}
```
> Verify each port `name` and param `name` against the backend node files while wiring (port names like `prompts`, `out`, `images` must match the actual `Port(name=...)`; correct any mismatch in the key and in the backend-reported name).

- [ ] **Step 2: Write the failing test**

`frontend/src/i18n/node-i18n.test.mjs`:
```js
// Run with: node frontend/src/i18n/node-i18n.test.mjs
import assert from 'node:assert/strict'
import { __setCatalogsForTest, setLang } from './index.js'
import { nodeTitle, nodeCategory, paramLabel } from './node-i18n.js'

__setCatalogsForTest(
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `node frontend/src/i18n/node-i18n.test.mjs`
Expected: FAIL — module `./node-i18n.js` not found.

- [ ] **Step 4: Implement `node-i18n.js`**

`frontend/src/i18n/node-i18n.js`:
```js
import { t } from './index.js'

// Vietnamese backend category → stable catalog slug.
const CATEGORY_SLUG = {
  'Đầu vào': 'input',
  'AI': 'ai',
  'Biến đổi': 'transform',
  'Đầu ra': 'output',
  'Khác': 'other',
}

export function nodeTitle(meta) {
  return t(`nodes.${meta.type}.title`, meta.title)
}
export function nodeDescription(meta) {
  return t(`nodes.${meta.type}.description`, meta.description)
}
export function nodeCategory(catVi) {
  const slug = CATEGORY_SLUG[catVi]
  return slug ? t(`category.${slug}`, catVi) : catVi
}
export function portLabel(type, port) {
  return t(`nodes.${type}.ports.${port.name}`, port.label)
}
export function paramLabel(type, param) {
  return t(`nodes.${type}.params.${param.name}.label`, param.label)
}
export function paramSupplementLabel(type, param) {
  return t(`nodes.${type}.params.${param.name}.supplement`, param.supplement_label)
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `node frontend/src/i18n/node-i18n.test.mjs`
Expected: prints `OK node-i18n`.

- [ ] **Step 6: Wire helpers into render sites**

Replace direct reads of `meta.title`/`meta.description`/`port.label`/`param.label`/`param.supplement_label`/category strings with the helper calls:
- `Palette.jsx`: node title → `nodeTitle(meta)`; description → `nodeDescription(meta)`; category grouping/header → `nodeCategory(cat)`.
- `ConnectNodeMenu.jsx`: same (title, description, category).
- `WorkflowNode.jsx`: title → `nodeTitle(meta)`; input/output labels → `portLabel(meta.type, port)`; param labels → `paramLabel`; supplement label → `paramSupplementLabel`.
- `NodeParamField.jsx`: param label → `paramLabel(meta.type, param)` (thread `meta.type`/`type` as a prop if not already available).

Because helpers call `t()` at render and components already re-render via `useT()` in their tree, the toolbar/Settings toggle updates node labels instantly. If a render site does not otherwise consume `useT`, add `const { lang } = useT()` there so it re-renders on language change (the `lang` value is unused but subscribes the component).

- [ ] **Step 7: Verify build + manual smoke**

Run: `npm run build --prefix frontend`
Expected: success. Manual: with backend running, switch to EN → node titles/descriptions/params in Palette and on canvas show English; switch to VI → show the backend Vietnamese.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/i18n/node-i18n.js frontend/src/i18n/node-i18n.test.mjs frontend/src/i18n/locales/en.json frontend/src/components/Palette.jsx frontend/src/components/ConnectNodeMenu.jsx frontend/src/components/WorkflowNode.jsx frontend/src/components/NodeParamField.jsx
git commit -m "feat(i18n): overlay node schema strings by stable id with vi fallback"
```

---

### Task 12: Backend error `code` + `params` (model + emit sites)

**Files:**
- Modify: `backend/app/models.py:31-37` (add `code`, `params` to `RunEvent`)
- Modify: `backend/app/engine.py` (node_error / run_error emit sites: ~114, ~182, ~212; parse errors ~35, ~49)
- Modify: `backend/app/main.py` (HTTP JSONResponse error sites — add `"code"`)
- Modify: `backend/app/oauth_routes.py` (error sites)
- Test: `backend/tests/test_error_codes.py`

**Interfaces:**
- Produces: every user-facing backend error response/event carries a stable `code` (lowercase snake_case) alongside the existing Vietnamese `message`/`error`. Optional `params` dict for dynamic templates. The Vietnamese text remains the fallback.

The canonical code list (assign these exact slugs):

| Site | Code |
|---|---|
| load_image no upload (inputs.py) | `load_image_missing` |
| save_image no input (output.py) | `save_image_no_input` |
| generate no prompt (generate.py) | `generate_no_prompt` |
| edit no image (edit.py) | `edit_no_image` |
| edit no prompt (edit.py) | `edit_no_prompt` |
| enhance no prompt (enhance_prompt.py) | `enhance_no_prompt` |
| extract no image (extract_region.py) | `extract_no_image` |
| extract no target (extract_region.py) | `extract_no_target` |
| provider no api key gemini | `gemini_no_api_key` |
| provider no api key openai | `openai_no_api_key` |
| provider no image returned | `provider_no_image` |
| provider no text returned | `provider_no_text` |
| provider unsupported text | `provider_no_text_support` |
| provider unsupported vision | `provider_no_vision_support` |
| object not found in image | `region_not_found` |
| unknown provider | `provider_unknown` |
| model config not found | `model_config_not_found` |
| codex not logged in | `oauth_not_logged_in` |
| codex session expired | `oauth_expired` |
| config name empty | `config_name_empty` |
| config provider invalid | `config_provider_invalid` |
| config name exists | `config_name_exists` |
| config not found | `config_not_found` |
| upload format unsupported | `upload_format_unsupported` |
| upload too large | `upload_too_large` |
| upload invalid image | `upload_invalid` |
| file not found | `file_not_found` |
| workflow not found | `workflow_not_found` |
| workflow exists | `workflow_exists` (already uses `"exists"` — keep that special key AND add `code`) |
| execution not found | `execution_not_found` |
| workflow invalid | `workflow_invalid` |
| workflow cycle | `workflow_cycle` |
| workflow edge invalid | `workflow_edge_invalid` |
| internal server error | `internal_error` |
| browser not available (oauth) | `browser_unavailable` |

> Long-tail provider-technical errors (Codex SSE timeout/incomplete, HTTP status, network) keep their Vietnamese message and may share `code: "provider_error"` — they are rare and the raw message is acceptable as fallback. Do NOT spend effort enumerating every one; cover the table above.

- [ ] **Step 1: Add fields to RunEvent**

Modify `backend/app/models.py` `RunEvent`:
```python
class RunEvent(BaseModel):
    type: str
    node_id: Optional[str] = None
    message: Optional[str] = None
    code: Optional[str] = None          # stable error slug for i18n; None for non-errors
    params: Optional[dict[str, Any]] = None  # dynamic values for the i18n template
    preview: Optional[str] = None
    outputs: Optional[dict[str, Any]] = None
    cached: bool = False
```

- [ ] **Step 2: Write the failing test**

`backend/tests/test_error_codes.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_model_config_empty_name_has_code():
    r = client.post("/api/model-configs", json={"name": "", "provider": "gemini"})
    assert r.status_code == 400
    body = r.json()
    assert body.get("code") == "config_name_empty"
    assert body.get("error")  # Vietnamese message preserved

def test_workflow_not_found_has_code():
    r = client.get("/api/workflows/__definitely_missing__")
    assert r.status_code == 404
    assert r.json().get("code") == "workflow_not_found"
```
> Confirm the test import path matches existing backend tests (e.g. they may use `from backend.app.main import app` or run with `backend/` on `sys.path`). Match the existing convention in `backend/tests/`.

- [ ] **Step 3: Run test to verify it fails**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_error_codes.py -v`
Expected: FAIL — `code` is `None`.

- [ ] **Step 4: Add `code` to HTTP error responses (main.py)**

For each error `JSONResponse` in `main.py`, add a `"code"` field. Example:
```python
return JSONResponse(status_code=400, content={"error": "Tên cấu hình không được để trống.", "code": "config_name_empty"})
```
Apply the mapping from the table to every listed site. Keep the Vietnamese `error` text unchanged. For the 409 workflow-exists response, keep `{"error": "exists", "name": name}` and add `"code": "workflow_exists"`.

- [ ] **Step 5: Add `code` (+ params) to node/run errors (engine.py + nodes)**

When raising node validation `ValueError`s, attach a code. Simplest pattern: define a tiny exception carrying a code, OR map known messages to codes at the emit site. Recommended — add an optional attribute on the raised error:
```python
# backend/app/nodes/_errors.py (new)
class NodeInputError(ValueError):
    def __init__(self, message: str, code: str, params: dict | None = None):
        super().__init__(message)
        self.code = code
        self.params = params or {}
```
Raise it in node `run()` methods, e.g. in `generate.py`:
```python
from ._errors import NodeInputError
raise NodeInputError("Node 'Tạo ảnh' cần prompt (nối vào cổng hoặc gõ trực tiếp).", "generate_no_prompt")
```
In `engine.py` where node errors are caught (~182) and emitted as `node_error`, read `getattr(e, "code", None)` and `getattr(e, "params", None)` into the `RunEvent`. Likewise for `run_error` parse failures (~35, ~49): emit `workflow_edge_invalid` / `workflow_cycle`; internal catch (~394) → `internal_error`; workflow validation (~349) → `workflow_invalid`.

- [ ] **Step 6: Run test to verify it passes**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_error_codes.py -v`
Expected: PASS.

- [ ] **Step 7: Run full backend test suite (no regressions)**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
Expected: no NEW failures vs. baseline. (Known pre-existing `test_engine_cache.py` failures are unrelated — see project memory.)

- [ ] **Step 8: Commit**

```bash
git add backend/app/models.py backend/app/main.py backend/app/engine.py backend/app/oauth_routes.py backend/app/nodes/ backend/tests/test_error_codes.py
git commit -m "feat(i18n): attach stable error codes to backend error responses and run events"
```

---

### Task 13: Frontend error translation + api.js wiring

**Files:**
- Modify: `frontend/src/api.js`
- Modify: error-display sites (`App.jsx` run socket handler; toast callers catching errors)
- Modify: `frontend/src/i18n/locales/en.json`, `vi.json`
- Test: extend `frontend/src/i18n/i18n.test.mjs` or add `error-i18n.test.mjs`

**Interfaces:**
- Consumes: `t` (Task 1), backend `code`/`params` (Task 12).
- Produces: `translateError(codeOrErr, fallbackMessage?, params?): string` in `frontend/src/i18n/index.js` (or a sibling) → `t('error.{code}', fallbackMessage, params)`; if no code, returns `fallbackMessage`.

- [ ] **Step 1: Add `error.*` catalog keys**

Author English in `en.json` and Vietnamese in `vi.json` for every code in the Task 12 table plus the frontend-authored api.js errors. Example slice (`en.json`):
```json
{
  "error.generate_no_prompt": "The Generate image node needs a prompt (connect a wire or type one).",
  "error.workflow_not_found": "Workflow not found.",
  "error.config_name_empty": "Configuration name cannot be empty.",
  "error.upload_failed": "Image upload failed.",
  "error.node_list_failed": "Could not load the node list from the backend.",
  "error.save_failed": "Save failed.",
  "error.generic": "Something went wrong."
}
```
`vi.json` mirrors each with the original Vietnamese text (copy from backend/api.js sources). Cover the full code table; for the long-tail `provider_error` code, add `"error.provider_error"` = "The provider returned an error." (en) / a Vietnamese equivalent (vi) — the raw backend `message` still shows when richer.

- [ ] **Step 2: Add `translateError` helper**

In `frontend/src/i18n/index.js`:
```js
// Translate a backend error by code, falling back to the raw backend message.
export function translateError(code, fallbackMessage, params) {
  if (!code) return fallbackMessage || t('error.generic')
  return t(`error.${code}`, fallbackMessage, params)
}
```

- [ ] **Step 3: Convert api.js literals**

Replace each `throw new Error('...')` in `api.js` with `throw new Error(t('error.<slug>'))` (import `t` from `./i18n/index.js`). For responses that already carry backend text, prefer the backend `code`: e.g. in `saveModelConfig`, parse `body.code` and throw `new Error(translateError(body.code, body.error))`. Keep the existing `err.code = 'exists'` branch working (it predates this; the workflow-exists flow in `App.jsx` checks `.code === 'exists'`).

- [ ] **Step 4: Translate run-socket errors in App.jsx**

Where the run WebSocket `node_error`/`run_error` events are turned into toasts, use `translateError(evt.code, evt.message, evt.params)` so EN users see English and VI users see the backend text.

- [ ] **Step 5: Verify build + tests + smoke**

Run: `npm run build --prefix frontend` (expect success).
Run: `node frontend/src/i18n/i18n.test.mjs` (and the error test if added) — expect OK.
Manual: in EN mode, trigger an error (e.g. run a Generate node with no prompt; save a config with empty name) → English toast. In VI mode → Vietnamese.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api.js frontend/src/App.jsx frontend/src/i18n/
git commit -m "feat(i18n): translate backend and frontend error messages by code"
```

---

### Task 14: Bilingual README

**Files:**
- Modify: `README.md` (becomes English, primary)
- Create: `README.vi.md` (current Vietnamese content)
- Reference: `images/` paths must stay valid from repo root (both files at root → unchanged relative paths).

- [ ] **Step 1: Move current Vietnamese README to README.vi.md**

```bash
git mv README.md README.vi.md
```

- [ ] **Step 2: Add cross-link header to README.vi.md**

Insert as the very first line of `README.vi.md`:
```markdown
> **Tiếng Việt** · [English](README.md)
```

- [ ] **Step 3: Create English README.md**

Create `README.md` as a faithful English translation of `README.vi.md`, preserving structure, code blocks, image embeds (`images/...` paths unchanged), and the tables. First line:
```markdown
> **English** · [Tiếng Việt](README.vi.md)
```
Translate all prose, headings, the feature list, the node table, and the macOS quarantine note. Keep commands, file paths, and code identifiers verbatim (do not translate `run.bat`, `backend\.venv`, etc.).

- [ ] **Step 4: Verify links + images**

Run: `git status` (confirm `README.md` modified + `README.vi.md` added).
Manual: preview both files; confirm cross-links resolve and images render.

- [ ] **Step 5: Commit**

```bash
git add README.md README.vi.md
git commit -m "docs: make README English (primary) with Vietnamese README.vi.md"
```

---

### Task 15: Final verification & self-review

- [ ] **Step 1: Grep for leftover Vietnamese in frontend JS/JSX (excluding catalogs/comments)**

Run (PowerShell-safe via Grep tool or):
```bash
grep -rnP '[\x{00C0}-\x{1EF9}]' frontend/src --include=*.jsx --include=*.js | grep -v 'i18n/locales' | grep -v '^\s*//'
```
Expected: only acceptable hits (comments, the category map in `node-i18n.js`). Investigate any user-facing literal still present and fold it into the right extraction task.

- [ ] **Step 2: Full builds + tests**

Run: `npm run build --prefix frontend` → success.
Run: `node frontend/src/i18n/i18n.test.mjs && node frontend/src/i18n/node-i18n.test.mjs` → both OK.
Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` → no new failures.

- [ ] **Step 3: End-to-end manual smoke**

Fresh localStorage (clear `iw-ui-settings`) → app loads in **English**. Toggle to VI from toolbar → all UI, node labels, and a triggered error switch to Vietnamese; reload → VI persists. Toggle back to EN.

- [ ] **Step 4: Update docs**

Add a short note to `docs/codebase-summary.md` (if present) describing the i18n layer (`frontend/src/i18n/`, catalogs, node overlay, backend `code`s). Commit:
```bash
git add docs/
git commit -m "docs: document i18n architecture in codebase summary"
```

---

## Self-Review

**Spec coverage:**
- English default + VI → Tasks 1, 3 (default `en`, toggle). ✓
- No new deps → Task 1 (hand-rolled). ✓
- Static UI extraction → Tasks 4–10. ✓
- Node overlay by ID + VI fallback → Task 11. ✓
- Backend error codes → Task 12; frontend translation → Task 13. ✓
- Settings toggle + toolbar quick toggle → Task 3. ✓
- localStorage persistence in `iw-ui-settings` → Task 1. ✓
- Bilingual README (EN primary) → Task 14. ✓
- Testing (resolver node test + backend pytest + manual) → Tasks 1, 11, 12, 15. ✓

**Placeholder scan:** Extraction tasks (4–10) intentionally specify namespace + procedure rather than transcribing every literal, because the exact source text lives in the files the executor reads; each task has concrete acceptance criteria (no VI literal remains; VI renders identically; build passes). All infrastructure, catalog (node + error), and backend tasks contain complete code.

**Type/name consistency:** `t(key, fallback?, params?)` signature consistent across Tasks 1, 11, 13. Node helper names (`nodeTitle`/`nodeDescription`/`nodeCategory`/`portLabel`/`paramLabel`/`paramSupplementLabel`) consistent between Task 11 interface and wiring. Error codes consistent between Task 12 table and Task 13 catalog keys (`error.{code}`).

## Open questions

- Exact `Port` `name` values for a few ports (e.g. enhance/extract output, combine_text input) must be confirmed against the backend node files during Task 11 wiring; keys are written to the expected names and corrected if they differ.
