---
title: Package app as self-contained Windows onedir exe
description: ''
status: completed
priority: P2
branch: feat/neutral-theme-redesign
tags: []
blockedBy: []
blocks: []
created: '2026-06-15T15:35:00.466Z'
createdBy: 'ck:plan'
source: skill
---

# Package app as self-contained Windows onedir exe

## Overview

Ship the app as a self-contained Windows program for non-dev users (no Python/Node installed). Collapse the 2-process dev setup (Vite 5173 + uvicorn 8000) into one backend process that also serves the pre-built React SPA same-origin, then freeze the Python side with PyInstaller (**onedir**). Frontend needs **zero code changes** (already uses relative `/api` + `location.host` WS). Keys stay UI-entered (SQLite), not baked into the exe.

Design doc: `plans/reports/brainstorm-design-260615-2230-package-app-single-exe-report.md`

**In scope:** Windows onedir exe, backend-serves-SPA, frozen writable data-dir fix, launcher + browser-open, build script, docs.
**Out of scope:** code-signing, installer (.msi/Inno), auto-update, Electron/Tauri, macOS/Linux.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Serve SPA and fix frozen data-dir](./phase-01-serve-spa-and-fix-frozen-data-dir.md) | Completed |
| 2 | [Desktop launcher entrypoint](./phase-02-desktop-launcher-entrypoint.md) | Completed |
| 3 | [PyInstaller spec and build script](./phase-03-pyinstaller-spec-and-build-script.md) | Completed |
| 4 | [Build verify and docs](./phase-04-build-verify-and-docs.md) | Completed |

## Dependencies

<!-- Cross-plan dependencies -->
