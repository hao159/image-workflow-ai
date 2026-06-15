---
phase: 3
title: PyInstaller spec and build script
status: completed
priority: P1
effort: 3h
dependencies:
  - 2
---

# Phase 3: PyInstaller spec and build script

## Overview
The packaging core: a PyInstaller **onedir** spec that bundles the Python runtime, all backend deps, and the built SPA; plus a one-shot PowerShell build script that builds the frontend and runs PyInstaller. Expect 1–2 iterate cycles on hidden-imports for this dep set (mechanical, not architectural).

## Requirements
- Functional: `build\build.ps1` produces `dist\ImageWorkflow\ImageWorkflow.exe` (onedir) bundling SPA + all deps.
- Non-functional: repeatable; uses `backend/.venv` Python (so bundled deps match `requirements.txt`).

## Architecture
- **Build flow (`build/build.ps1`):**
  1. `npm run build --prefix frontend` → `frontend/dist`.
  2. Ensure PyInstaller in backend venv: `backend\.venv\Scripts\pip install pyinstaller` (build-time only; NOT added to `requirements.txt`).
  3. `backend\.venv\Scripts\pyinstaller build\imageworkflow.spec --noconfirm --clean`.
- **Spec (`build/imageworkflow.spec`)** — entry `backend/desktop_app.py`:
  - `datas`: bundle `frontend/dist` → `frontend_dist` (matches `config.SPA_DIR` when frozen). `collect_data_files` for `certifi`, and any `google`/`openai` package data.
  - `hiddenimports`: uvicorn loop/protocol modules (`uvicorn.lifespan.on`, `uvicorn.loops.asyncio`, `uvicorn.protocols.http.httptools_impl` / `h11_impl`, `uvicorn.protocols.websockets.websockets_impl`), `websockets`, `httptools`, `app.main` and submodules (`app.engine`, `app.nodes.*`, `app.providers.*`, `app.oauth_routes`, `app.db`, `app.cache`), `google.genai`, `openai`, `pydantic`, `multipart`.
  - Prefer `collect_submodules('app')`, `collect_submodules('uvicorn')`, `collect_all('google')` / `collect_all('openai')` where blanket inclusion is simpler than enumerating.
  - `console=True` for first builds (see errors); flip to `False` later (Phase 4 decision).
  - `name='ImageWorkflow'`, onedir (default — no `--onefile`).
- **Dynamic node/provider discovery:** `app/nodes` + `app/providers` use decorator/registry imports. If any provider/node is imported dynamically (not statically), PyInstaller misses it → add via `collect_submodules('app.nodes')` / `collect_submodules('app.providers')`. Verify by listing every module in those dirs during the spec write.

## Related Code Files
- Create: `build/imageworkflow.spec`.
- Create: `build/build.ps1`.
- Read for context: `backend/app/providers/__init__.py`, `backend/app/nodes/__init__.py` (confirm import style → decide static vs `collect_submodules`).

## Implementation Steps
1. Inspect `app/providers/__init__.py` and `app/nodes/__init__.py` to confirm whether all providers/nodes are statically imported (registry pattern). Note any dynamic imports.
2. Write `build/imageworkflow.spec` with `Analysis` → entry `backend/desktop_app.py`, `pathex=['backend']`, the `datas`/`hiddenimports` above, `collect_submodules`/`collect_all` helpers, then `EXE`+`COLLECT` (onedir), `name='ImageWorkflow'`, `console=True`.
3. Write `build/build.ps1` per the build flow (fail-fast: check `$?` after each native step since PowerShell 5.1 lacks `&&`).
4. Run `build\build.ps1`. Iterate on `ModuleNotFoundError` / missing-data errors → add to `hiddenimports`/`datas` until it builds clean.

## Success Criteria
- [ ] `build\build.ps1` completes and emits `dist\ImageWorkflow\ImageWorkflow.exe`.
- [ ] No `ModuleNotFoundError` at startup; server boots from the exe.
- [ ] Bundled SPA present under `dist\ImageWorkflow\_internal\frontend_dist` (or spec-equivalent) and served.
- [ ] All providers + node types appear (`/api/node-types`, `/api/providers` return full lists) — confirms registry imports bundled.

## Risk Assessment
- **Missing dynamic imports (providers/nodes):** highest-risk gap — mitigate with `collect_submodules('app.nodes'|'app.providers')`.
- **`google-genai`/`openai` data files:** use `collect_all`; missing certs → httpx TLS errors at runtime → add `certifi` data.
- **uvloop on Windows:** not used (asyncio loop) — ensure spec doesn't force uvloop.
- **Antivirus false-positive on fresh exe:** onedir reduces it; full mitigation (code-signing) is out of scope.
