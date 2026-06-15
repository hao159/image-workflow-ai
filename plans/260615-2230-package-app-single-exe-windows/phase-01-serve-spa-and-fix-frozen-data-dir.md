---
phase: 1
title: Serve SPA and fix frozen data-dir
status: completed
priority: P1
effort: 2h
dependencies: []
---

# Phase 1: Serve SPA and fix frozen data-dir

## Overview
Make the backend serve the pre-built React SPA same-origin and make data dirs resolve to a writable, persistent location when frozen. This is the foundation — once done, the app runs single-origin even in dev (build frontend, open `http://127.0.0.1:8000`), independent of PyInstaller.

## Requirements
- Functional: backend serves SPA at `/`; all `/api/*` + `/ws/run` routes keep priority; data persists next to the exe when frozen.
- Non-functional: no frontend code changes; dev workflow (Vite 5173) still works unchanged.

## Architecture
- **Route order (Starlette matches in registration order):** keep all API routes + `@app.websocket("/ws/run")` registered first, then `app.mount("/", StaticFiles(...))` LAST so static is the catch-all. No client-side router in frontend (`frontend/package.json` deps = `@xyflow/react`,`react`,`react-dom`) → `StaticFiles(html=True)` at `/` is sufficient; no SPA history-fallback needed.
- **Frozen detection:** `getattr(sys, "frozen", False)`.
  - `ROOT_DIR` (data) = `Path(sys.executable).parent` when frozen (writable, persistent, next to exe) — else current `parents[2]` (project root).
  - `SPA_DIR` = `Path(sys._MEIPASS) / "frontend_dist"` when frozen — else `ROOT_DIR / "frontend" / "dist"`.
- `load_dotenv(ROOT_DIR / ".env")` keeps working: optional `.env` next to exe is read; absence is fine (keys via UI).

## Related Code Files
- Modify: `backend/app/config.py` — add `import sys`; frozen-aware `ROOT_DIR`; export `SPA_DIR`.
- Modify: `backend/app/main.py` — mount `StaticFiles` after routes; serve SPA only if `SPA_DIR` exists (dev without build → skip mount, log hint).

## Implementation Steps
1. `config.py`: add `import sys`. Before `ROOT_DIR = ...`, branch:
   ```python
   if getattr(sys, "frozen", False):
       ROOT_DIR = Path(sys.executable).parent          # writable, next to exe
       SPA_DIR = Path(sys._MEIPASS) / "frontend_dist"   # bundled by PyInstaller
   else:
       ROOT_DIR = Path(__file__).resolve().parents[2]
       SPA_DIR = ROOT_DIR / "frontend" / "dist"
   ```
   Keep `load_dotenv(ROOT_DIR / ".env")` and all dir creation as-is (now relative to the resolved ROOT_DIR).
2. `main.py`: `from fastapi.staticfiles import StaticFiles` and `from . import config`. At the **end** of the module (after every route + the websocket), add:
   ```python
   if config.SPA_DIR.is_dir():
       app.mount("/", StaticFiles(directory=config.SPA_DIR, html=True), name="spa")
   ```
3. Verify API routes still resolve (mount is last → `/api/*` and `/ws/run` win).
4. Build the SPA once for manual verification: `npm run build --prefix frontend` (outputs `frontend/dist`).

## Success Criteria
- [ ] `config.py` resolves `ROOT_DIR`/`SPA_DIR` correctly in both frozen and non-frozen branches (unit-checkable via monkeypatching `sys.frozen`).
- [ ] With `frontend/dist` built, running `backend/run_server.py` and opening `http://127.0.0.1:8000/` loads the app (SPA served by backend, no Vite).
- [ ] `/api/node-types` and a `/ws/run` connection still work on port 8000 directly.
- [ ] Dev mode unchanged: `npm run dev` on 5173 + backend still works.

## Risk Assessment
- **Mount shadowing API:** mitigated by registering mount LAST. If any `/api` returns the SPA HTML, the mount was added too early → move it.
- **Dev without build:** `SPA_DIR` missing → skip mount (guarded by `is_dir()`), backend still serves API for Vite proxy.
