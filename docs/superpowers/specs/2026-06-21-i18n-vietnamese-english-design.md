# Design: Internationalization (i18n) — English + Vietnamese

**Date:** 2026-06-21
**Status:** Approved (pending spec review)
**Scope:** Image Workflow desktop app — full UI localization

## Goal

Make the app bilingual (English default, Vietnamese secondary). Cover **all** user-facing
strings: frontend static UI, backend-defined node schema (title/description/param labels),
and backend error messages. Bilingual README.

## Decisions (locked)

| # | Decision |
|---|---|
| Languages | English (`en`) + Vietnamese (`vi`) |
| Default | `en` (English) when no stored preference |
| Mechanism | Lightweight custom i18n in frontend — **no new dependencies** |
| Backend strings | Node schema unchanged; frontend overlays by stable ID. Errors get a stable `code` |
| Selection UX | Toggle in ⚙ Settings (Appearance tab) **+** quick `VI \| EN` toggle on toolbar |
| Persistence | `lang` stored in existing `iw-ui-settings` localStorage object |
| Node VI strings | DRY — `vi.json` omits node entries, falls back to backend Vietnamese source |
| README | `README.md` → English (primary), `README.vi.md` → Vietnamese; cross-links at top |

## Architecture

Single lightweight i18n layer in the frontend. Backend stays nearly unchanged — only adds a
stable `code` to user-facing errors so the frontend can translate them.

```
frontend/src/i18n/
├── index.js            # module-level currentLang + t() usable ANYWHERE (incl. non-React) + get/setLang
├── i18n-provider.jsx   # React context: re-renders UI tree on language change
├── use-t.js            # hook → { t, lang, setLang }
└── locales/
    ├── en.json         # English — FULL catalog (default display)
    └── vi.json         # Vietnamese — full static UI; node section omitted (fallback to backend)
```

**Key mechanic:** `t()` reads `currentLang` at the module level (so `api.js` and other non-React
modules work too). `I18nProvider` only re-renders the React tree when language changes. Language
switch is **instant** — no API refetch.

### The `t()` resolver

```js
t('toolbar.run')                        // → catalog[lang]['toolbar.run']
t(`nodes.${node.name}.title`, beTitle)  // node: missing key → fall back to backend string
t('error.saveFailed', '{n} errors', {n}) // simple {var} interpolation
```

Fallback chain: `catalog[lang][key]` → provided fallback arg → `key` string. **Never throws** on
missing key.

## String groups & handling

| Group | Source | Handling |
|---|---|---|
| Static UI (toolbar, settings, menu, toast, modals) | frontend JSX/JS (~20 files) | Extract to keys → `t('area.key')`; both `en.json` + `vi.json` complete |
| Frontend-authored errors (`api.js`) | `throw new Error('...')` | Convert to `t('error.xxx')` |
| Node title/description/param label | backend Python schema | **ID overlay**: `en.json` has full English; `vi.json` omits → backend Vietnamese fallback |
| Backend runtime errors (`body.error`, WS node errors) | engine/routes Python | Backend adds stable `code`; frontend `t('error.{code}', beMsg)`; missing code → show raw text |

## Components

### Frontend i18n core (new)
- `index.js`: `currentLang` (module state), `getLang()`, `setLang(lang)` (writes localStorage +
  dispatches `iw-lang-change` event), `t(key, fallback?, params?)`.
- `i18n-provider.jsx`: subscribes to `iw-lang-change`, holds lang in state, re-renders children.
- `use-t.js`: `useT()` → `{ t, lang, setLang }`.
- `locales/en.json`, `locales/vi.json`: flat or shallow-nested key catalogs.

### Settings UI (modify)
- `settings-appearance-tab.jsx`: add a segmented control **English / Tiếng Việt** matching the
  existing theme control. On change → `setLang()`.

### Toolbar quick toggle (modify)
- In `App.jsx` toolbar, add a compact `VI | EN` segmented toggle beside ⚙ Settings. Reads/writes
  the same `iw-ui-settings.lang`, so it stays in sync with the Settings control.

### Frontend string extraction (modify ~20 files)
- Replace hardcoded Vietnamese with `t('...')`. Key namespaces: `toolbar.*`, `settings.*`,
  `palette.*`, `toast.*`, `menu.*`, `modal.*`, `error.*`, `history.*`, `library.*`.
- `api.js` error strings → `t('error.*')`.

### Node schema overlay (modify)
- Where node title/description/param labels render (`Palette.jsx`, `WorkflowNode.jsx`,
  `NodeParamField.jsx`, `ConnectNodeMenu.jsx`): wrap with `t('nodes.{type}.title', beTitle)`,
  `t('nodes.{type}.params.{param}.label', beLabel)`, etc.
- `en.json` `nodes.*` = full English. `vi.json` `nodes.*` omitted → backend Vietnamese.

### Backend error codes (modify)
- Add a stable `code` field to user-facing error responses and WS node-error events.
- Sites to cover (confirm exhaustively during planning by scanning `backend/app/`): model-config
  save, provider model listing, OAuth start/status, node execution failures (engine), workflow
  save/load/delete where surfaced.
- Codes are **stable English slugs** (e.g. `save_failed`, `model_list_failed`). Not tied to plan
  artifacts. Errors without a code still render (raw text) — but for English-default correctness,
  coverage must be thorough.

### README (modify/add)
- `README.md` → English translation (becomes the primary GitHub-rendered file).
- `README.vi.md` → current Vietnamese content moved here.
- Both files start with a cross-link line: `English | Tiếng Việt`.

## Data flow

1. Boot: read `lang` from `iw-ui-settings` localStorage; absent → `'en'`. Set `currentLang`,
   mount `I18nProvider`.
2. User toggles (Settings or toolbar) → `setLang()` updates `currentLang`, writes localStorage,
   dispatches `iw-lang-change`.
3. `I18nProvider` re-renders the tree → every `t()` returns the new language.
4. Node schema fetched once; overlays recompute on re-render → no refetch needed.

## Error handling / edge cases

- Missing translation key → fallback chain prevents crashes.
- Backend error without `code` → frontend shows raw backend text (Vietnamese). Acceptable
  degradation; planning aims for full code coverage so this is rare.
- Interpolation with missing param → leave `{var}` literal rather than throw.
- localStorage unavailable / corrupt → default `'en'`, same try/catch pattern as `ui-settings.js`.

## Testing

- **Backend (pytest, exists):** assert user-facing error responses include the expected `code`.
- **Frontend (no test infra today):** a plain `node`-runnable test for the `t()` resolver
  (resolution, fallback chain, `{var}` interpolation) — no new dependency. Plus manual smoke test:
  toggle EN↔VI from both Settings and toolbar; verify static UI, node labels, and a triggered
  error all switch language; verify default is English on fresh localStorage.

## Out of scope (YAGNI)

- Languages beyond EN/VI (architecture allows adding later via a new `locales/*.json`).
- Pluralization rules beyond simple `{var}` interpolation (VI has no plurals; EN cases here are trivial).
- Locale-aware number/date formatting.
- Translating code comments or developer-facing logs.

## Open questions

None — all decisions locked.
