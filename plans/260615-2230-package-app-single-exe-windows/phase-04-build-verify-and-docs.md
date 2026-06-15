---
phase: 4
title: Build verify and docs
status: completed
priority: P2
effort: 2h
dependencies:
  - 3
---

# Phase 4: Build verify and docs

## Overview
Verify the packaged exe behaves like the acceptance scenario on a clean-as-possible environment, decide windowed vs console, and document how to build + run the distributable.

## Requirements
- Functional: exe runs end-to-end with data persistence; build process documented.
- Non-functional: verification done from a fresh data dir (no pre-seeded `data.db`/`cache`) to simulate first run.

## Architecture
- **Clean-run verification:** copy `dist\ImageWorkflow\` to a fresh folder (or temp dir with no sibling `data.db`/`cache/`) → double-click → confirm dirs get created next to the exe (validates Phase 1 frozen `ROOT_DIR`).
- **Console vs windowed:** after a clean successful run, flip `console=False` in the spec for a no-terminal launch; keep a note on how to re-enable for debugging.
- **Docs:** add a "Build / Distribute" section to `README.md`; optionally update `docs/deployment-guide.md` if present.

## Related Code Files
- Modify: `README.md` (new "Đóng gói / Distribute (Windows exe)" section).
- Modify (optional, if exists): `docs/deployment-guide.md`, `docs/codebase-summary.md`.
- Modify (decision): `build/imageworkflow.spec` (`console` flag).

## Implementation Steps
1. Build via `build\build.ps1` (Phase 3 output).
2. Copy `dist\ImageWorkflow` to a fresh location with no existing data → run `ImageWorkflow.exe`.
3. Walk the acceptance scenario: browser opens → ⚙ Settings → add a provider config (e.g. Gemini key) → build a small workflow → ▶ Run → image renders. Close, reopen → workflow + history persisted (validates DB next to exe).
4. Run the `fake` provider path for a token-free smoke test.
5. Flip `console=False` in spec, rebuild, confirm it still launches + opens browser (no stray terminal). Keep console build documented for troubleshooting.
6. Write README "Build / Distribute" section: prerequisites (`backend/.venv` populated, `frontend` deps installed), command (`build\build.ps1`), output path, how data dir works (next to exe), AV/SmartScreen note, console-debug toggle.

## Success Criteria
- [ ] Clean-folder run creates `data.db` + `cache/`/`uploads/`/`outputs/`/`workflows/` next to the exe.
- [ ] Full acceptance scenario passes: configure key → run workflow → image renders → persists across restart.
- [ ] `fake` provider smoke test passes (offline, no token).
- [ ] Windowed build (`console=False`) launches with no terminal; console toggle documented.
- [ ] README documents build + run + data-location + AV note.

## Risk Assessment
- **Cannot truly test "no Python machine" locally:** mitigate by running from a fresh folder and trusting onedir self-containment; note as residual risk (ideal: test on a second machine/VM).
- **Windowed mode hides startup errors:** keep console build as the documented debug path.
- **First-run latency / AV scan:** document expected behavior so users don't kill the process.
