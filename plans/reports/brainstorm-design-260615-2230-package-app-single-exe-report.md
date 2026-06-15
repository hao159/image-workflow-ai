# Brainstorm Design — Package Image Workflow as Self-Contained Windows exe

**Date:** 2026-06-15 · **Status:** Approved (design) · **Branch:** feat/neutral-theme-redesign

## Problem
Ship the app as a self-contained Windows program for non-dev users (no Python/Node installed). Currently 2 dev processes: Vite (5173) proxying `/api` + `/ws` → uvicorn (8000).

## Decisions (user-confirmed)
- **Target:** fully self-contained — bundle Python runtime + all deps.
- **Form:** PyInstaller **onedir** (folder w/ exe + libs), not onefile.
- **API keys:** entered via ⚙ Settings UI at runtime (already stored in SQLite) — NOT baked into exe.

## Key codebase facts (scout)
- Frontend uses RELATIVE urls: `/api/...` (`frontend/src/api.js:2`) + `ws://${location.host}/ws/run` (`api.js:116`) → works same-origin, zero FE change.
- Data dirs = `parents[2]` of `config.py` (`config.py:6-17`): `data.db`, `cache/`, `uploads/`, `outputs/`, `workflows/`, `logs/`. **Breaks when frozen** (points into temp extract dir).
- Critical uvicorn setting: `ws_ping_interval=None` (`run_server.py:24`) — must preserve in frozen launcher or long AI nodes drop WS.
- Codex OAuth reads `~/.codex/auth.json` (home dir) — bundle-safe.
- Deps: fastapi, uvicorn[standard], pydantic, pillow, google-genai, openai, httpx, websockets, python-multipart, python-dotenv.

## Chosen approach: FastAPI-serves-SPA + PyInstaller onedir
Collapse 2 processes → 1 backend that also serves the pre-built React SPA same-origin. (Only viable self-contained path: no Node on target ⇒ SPA must be served by backend.)

### Touchpoints (4)
1. **`backend/app/main.py`** — mount built SPA via `StaticFiles(..., html=True)` AFTER api routes; SPA catch-all returns `index.html`. CORS stays for dev (same-origin needs none).
2. **`backend/app/config.py`** — when `sys.frozen`: `ROOT_DIR = Path(sys.executable).parent` (writable, persistent next to exe). SPA dir from `sys._MEIPASS` when frozen else `frontend/dist`.
3. **`backend/desktop_app.py` (new)** — frozen entrypoint: uvicorn programmatic w/ `ws_ping_interval=None`, no reload, port-fallback if 8000 busy, then `webbrowser.open`.
4. **`build/imageworkflow.spec` + `build.ps1` (new)** — `npm run build` → PyInstaller onedir w/ hidden-imports / collect-data for uvicorn+websockets+httptools, google.genai, openai, pydantic, certifi, pillow; bundle `frontend/dist` as data.

### Rejected
- **B. Launcher spawning 2 servers** — needs Node bundled; dual-process. ✗ (self-contained constraint).
- **C. Tauri/Electron window** — nicer UX but 2nd runtime + complexity. YAGNI → future polish.
- **onefile** — slow extract, antivirus FPs. ✗ (user chose onedir).

## Risks
- PyInstaller hidden-imports tuning for google-genai/openai/uvicorn — expect 1–2 iterate cycles (mechanical, not architectural).
- Bundle ~150–250 MB.
- Unsigned exe → SmartScreen/AV warning possible (code-signing out of scope).

## Scope
**In:** Windows onedir exe, backend-serves-SPA, frozen writable-dir fix, launcher+browser-open, build script.
**Out:** code-signing, installer (.msi/Inno), auto-update, Electron/Tauri, macOS/Linux.

## Acceptance
Clean Windows (no Python/Node): double-click `ImageWorkflow.exe` → browser opens app → add provider key in Settings → build+run workflow → images render → data persists across restarts.

## Open questions
None.
