# Neutral Theme Redesign: System/Light/Dark Theming in React Flow Editor

**Date**: 2026-06-14 21:09  
**Severity**: Medium  
**Component**: Frontend UI (React Flow node editor)  
**Status**: Resolved  

## What Happened

Completed full frontend redesign of the React Flow node-editor UI. Replaced dark-only, AI-flavored aesthetic (violet #7c5cff, glow/scan effects, neon accents) with neutral professional style (soft blue #3b6cf0, flat design, no visual gimmicks). Added system/light/dark theme switcher with localStorage persistence.

**Branch**: `feat/neutral-theme-redesign` | **Commit**: `fea0aa1`

## Implementation Summary

**Phase 1: Token Architecture**  
Split CSS `:root` into shared + dark + light token sets, keyed on `<html data-theme>`. Tokenized ~23 hardcoded colors into custom properties (`--primary`, `--edge-*`, `--overlay-scrim`, `--badge-*`, `--rf-grid`, `--warn`, etc.). This made theme switching essentially free at runtime.

**Phase 2: Theme API & System Detection**  
Built `ui-settings.js`: `getThemeSetting()`, `setThemeSetting()`, `resolveTheme()` (system preference fallback), `applyTheme()` (writes to `<html data-theme>`), and `initThemeWatcher()` (CustomEvent `iw-theme-change`). Applied theme in `main.jsx` **before** `createRoot().render()` to prevent FOUC. Wired segmented control (Hệ thống/Sáng/Tối) in SettingsModal.

**Phase 3: Flat Restyle**  
Updated design tokens (radius: 7/10/14 → 6/8/10, flat button styles, 1px node borders, lighter shadows). All changes via token values—component CSS unchanged.

**Phase 4: Icon & Effect Defaults**  
Swapped `SparklesIcon` for neutral `WandIcon`. Changed default run indicator from 'glow' to 'solid' (glow/scan/pulse now opt-in). Wired React Flow `<Background color>` to theme by reading `getComputedStyle('--rf-grid')` on theme change.

**Phase 5: Verification**  
4 vite build passes. 3 code reviews all passed. Phase 1 concern re: unused `--rf-grid` token deferred to Phase 4 (now wired). No docs/ directory existed; updated README with theme note.

## Technical Gotchas

**CSS Specificity & Source Order**  
`:root, :root[data-theme='dark']` vs `:root[data-theme='light']` — light wins via source order at equal specificity. Order matters.

**React Flow Color Prop Limitation**  
`<Background color>` takes raw hex, not CSS variables. Workaround: read theme color via `getComputedStyle('--rf-grid')` on theme change. **Critical**: `applyTheme()` must set `data-theme` *before* dispatching `iw-theme-change` event so listeners see updated computed values.

**FOUC Prevention**  
Applying theme in `main.jsx` before render eliminates flash. Any earlier theme application (e.g., in index.html via script) would be safer but this ordering works.

**Existing localStorage Not Migrated**  
Changing `runEffect` default to 'solid' only affects new users. Existing localStorage values untouched—no migration logic added.

**Image Lightbox Exception**  
Media viewer intentionally dark in both themes (preserves image viewing contrast). Documented in CSS.

## Concerns & Open Items

- **Contrast warning**: `--text-faint` (~3:1 on white) used only for hints; reviewer flagged as potential tweak. Acceptable for hint text but monitor.
- **Visual QA**: Full theme validation across light/dark UI is pending user review (design sign-off).

## What We Tried

1. **Direct color overrides** → rejected; went with token architecture (cleaner, scalable).
2. **React Flow theme prop** → doesn't exist for grid; used computed styles instead.
3. **FOUC via CSS in head** → worked but fragile; moved to JS in main.jsx for reliability.
4. **Auto localStorage sync** → too much magic; explicit `setThemeSetting()` call keeps intent clear.

## Root Cause Analysis

The initial design mixed business logic (glow effects) with visual identity (neon accents), making "neutral restyle" tangled. Token-first architecture decoupled visual tokens from layout, letting theme toggle become a single data attribute. Phase ordering (architecture → API → style → effect → verification) avoided churn—each phase left prior work untouched.

## Lessons Learned

1. **Token architecture pays for itself**: All-CSS-custom-properties :root made theme switching trivial; component code never touched.
2. **Apply theme before render**: FOUC avoidance is non-negotiable for UX; theme setup in `main.jsx` is the right layer.
3. **React Flow requires workarounds for theming**: No native CSS variable support for Background color; computed style fallback is pragmatic.
4. **Explicit API > Auto-magic**: `setThemeSetting()` + event dispatch is clearer than global listeners or React context chains for this use case.
5. **Test specificity early**: CSS source order determines light/dark token precedence—verify in browser dev tools, not in code review.

## Next Steps

1. **User visual QA**: Validate light/dark theme appearance against design intent.
2. **Contrast audit**: Review `--text-faint` usage; tighten if needed.
3. **Deploy & monitor**: Roll to production; watch for FOUC reports in light/dark transitions.
4. **Document theme API**: Add brief JSDoc to `ui-settings.js` for future maintainers (theme application order, event flow).
