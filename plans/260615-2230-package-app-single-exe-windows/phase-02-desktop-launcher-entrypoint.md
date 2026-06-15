---
phase: 2
title: Desktop launcher entrypoint
status: completed
priority: P1
effort: 1.5h
dependencies:
  - 1
---

# Phase 2: Desktop launcher entrypoint

## Overview
A single frozen entrypoint that boots uvicorn programmatically (preserving the critical WS keepalive setting), picks a free port if 8000 is taken, then opens the default browser to the app. This is what PyInstaller turns into `ImageWorkflow.exe`.

## Requirements
- Functional: double-click starts server on `127.0.0.1`, opens browser to the served SPA, runs until window/console closed.
- Non-functional: MUST reuse `ws_ping_interval=None` / `ws_ping_timeout=None` (from `run_server.py:24`) — otherwise long AI nodes (>40s) drop the WS and images don't render.

## Architecture
- New `backend/desktop_app.py`. Imports the app via `app.main:app` (same string uvicorn uses), with `app_dir` set so it works frozen and from source.
- **Port selection:** try 8000; if bound, ask OS for a free port (`socket` bind to port 0) → use it. Pass the chosen port to both uvicorn and `webbrowser.open`.
- **Browser open after server is ready:** open in a short-delay background `threading.Timer` (server is blocking in main thread). Opening slightly early is fine — browser retries/loads once uvicorn is up.
- No `--reload` (reload + frozen don't mix). Run with `uvicorn.run(...)` blocking.

## Related Code Files
- Create: `backend/desktop_app.py`.
- Reference (do not duplicate logic unnecessarily): `backend/run_server.py` (WS settings source of truth).

## Implementation Steps
1. Create `backend/desktop_app.py`:
   ```python
   """Frozen desktop entrypoint: boot uvicorn + open browser. No --reload."""
   import socket, threading, webbrowser
   from pathlib import Path
   import uvicorn

   def _free_port(preferred=8000):
       with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
           try:
               s.bind(("127.0.0.1", preferred)); return preferred
           except OSError:
               s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
               s2.bind(("127.0.0.1", 0)); port = s2.getsockname()[1]; s2.close(); return port

   def main():
       port = _free_port(8000)
       url = f"http://127.0.0.1:{port}"
       threading.Timer(1.5, lambda: webbrowser.open(url)).start()
       uvicorn.run(
           "app.main:app",
           app_dir=str(Path(__file__).resolve().parent),
           host="127.0.0.1", port=port,
           ws_ping_interval=None, ws_ping_timeout=None,  # see run_server.py
       )

   if __name__ == "__main__":
       main()
   ```
2. Smoke test from source (after Phase 1 build): `backend\.venv\Scripts\python backend\desktop_app.py` → browser opens, app loads, a workflow runs.
3. Confirm a long-running node (use `fake` provider or a real AI node) keeps its WS alive past 40s.

## Success Criteria
- [ ] `python backend/desktop_app.py` starts server, auto-opens browser to the SPA.
- [ ] Port fallback works when 8000 is already in use (start two instances).
- [ ] WS stays connected through a >40s node run (no "keepalive ping timeout").

## Risk Assessment
- **Browser opens before server ready:** 1.5s timer + browser auto-retry covers it; acceptable for local startup.
- **`app_dir` resolution when frozen:** `__file__` of `desktop_app.py` resolves inside the bundle; `app.main` import path validated in Phase 3 hidden-imports.
