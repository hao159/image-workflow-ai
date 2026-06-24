# i18n — English + Vietnamese (default English)

Date: 2026-06-22

## What

Made the app bilingual (EN default, VI). Covers frontend UI, backend-defined node
schema, and backend error messages. README split into `README.md` (EN, primary) +
`README.vi.md` (VI).

## Architecture

Lightweight custom i18n in the frontend — **no new dependency**.

- `frontend/src/i18n/index.js` — module-level `currentLang` + `t(key, fallback?, params?)`
  usable anywhere (React and plain modules like `api.js`). `registerCatalogs(en, vi)`
  installs catalogs (kept out of the core so the `.mjs` node tests run under bare node).
  `setLang` persists `lang` in the existing `iw-ui-settings` localStorage object and fires
  `iw-lang-change`.
- `frontend/src/i18n/i18n-provider.jsx` + `use-t.js` — `<I18nProvider>` re-renders the tree
  on language change; `useT()` → `{ t, lang, setLang }`. Provider is outermost in `main.jsx`;
  `load-catalogs.js` is imported first so catalogs exist before render.
- `frontend/src/i18n/locales/en.json` / `vi.json` — flat dotted keys. `en.json` is full
  (default display). `vi.json` carries static UI but **omits node-schema keys** — VI falls
  back to the backend Vietnamese source (DRY).
- `frontend/src/i18n/node-i18n.js` — overlays node schema by stable id:
  `nodes.<type>.title|description`, `nodes.<type>.inputs|outputs.<portName>` (port keys are
  **direction-namespaced** because some nodes reuse a port name across input/output, e.g.
  `enhance_prompt` `text`), `nodes.<type>.params.<name>.label|supplement`, and
  `category.<slug>`. `t(key, backendString)` so VI falls back to the backend label.

### Backend

- `RunEvent` (and HTTP error responses) gained a stable `code` (+ optional `params`); the
  Vietnamese `message`/`error` text stays as the fallback. `NodeInputError` /
  `ProviderErrorWithCode` carry `.code`/`.params`; the engine reads them via
  `getattr(e, "code", None)` so plain `ValueError`s still work.
- The frontend `translateError(code, fallbackMessage, params)` maps `error.<code>` →
  localized text, falling back to the raw backend message when a code/translation is missing.

## Selecting language

Toggle in ⚙ Settings (Appearance tab) **and** a compact `VI | EN` quick toggle on the
toolbar — both read/write the same `iw-ui-settings.lang`, switch instantly, no refetch.

## Tests

`node frontend/src/i18n/{i18n,node-i18n,error-i18n}.test.mjs` (resolver, node overlay +
VI fallback, error translation). Backend `backend/test_error_codes.py` (error responses
carry codes). Pre-existing `test_engine_cache.py` failures are unrelated.
