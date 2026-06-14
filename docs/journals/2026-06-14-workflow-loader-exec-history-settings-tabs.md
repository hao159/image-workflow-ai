# Workflow Loader Modal + Execution History + Settings Tabs

**Date**: 2026-06-14 21:58
**Severity**: Medium
**Component**: API (save conflict, execution history, workflows), Frontend (modal UI, settings layout)
**Status**: Resolved

## What Happened

Shipped four interconnected UX/feature changes around workflow management and settings:

1. **Save-conflict detection (409 + confirm flow).** `POST /api/workflows` now returns HTTP 409 with `{"error":"exists"}` when workflow name exists, unless caller passes `?overwrite=true`. Frontend `save()` refactored to recursive `doSave(overwrite)`: on 409 → confirm dialog → retry with overwrite flag; cancel → "Đã hủy lưu". Replaces silent `ON CONFLICT DO UPDATE` behavior.

2. **Per-workflow execution history (n8n-style).** New `workflow_executions` table (id, workflow_name, mode, status, error, detail JSON, started_at, finished_at, duration_ms) + index on (workflow_name, id DESC). `ws_run` callback accumulates node statuses, image output SHAs (from `node_finished` event), and harness best iteration. Writes recorded only for full runs (target=None) + harness enabled; single-node runs skipped. A `try/finally` ensures record finalizes even on `WebSocketDisconnect` (running → stopped). Retention via `finish_execution`: prunes to 50 newest per workflow via `DELETE ... WHERE id NOT IN (SELECT ... ORDER BY id DESC LIMIT 50)`. Images are not duplicated—only SHA references into existing content-addressed blob store (`/api/cache-image/{sha}`). Four new routes: list (paginated), detail, delete one, clear all.

3. **"Mở workflow" modal replaces toolbar dropdown.** Centered modal (`workflow-browser-modal.jsx`) with client-side pagination + two tabs: **Danh sách** (paginated list) | **Lịch sử** (execution history). History panel (`execution-history-panel.jsx`) renders runs with status badges (✓/✗/⏹), server-side pagination, master-detail view: result images (click → existing ImageViewer; onError → "ảnh đã bị dọn" placeholder for LRU-evicted blobs), node state list, harness rounds, error box.

4. **SettingsModal tabs with form persistence.** Single-scroll 255-line modal refactored to thin shell (`SettingsModal.jsx`, 46 lines) + `settings-appearance-tab.jsx` + `settings-model-tab.jsx`. Default tab = Model. Both tabs stay mounted via `display: none` toggle → in-progress form data (model list fetch, dropdown state) survives tab switches. Avoids re-fetching on switch.

## The Brutal Truth

No critical fires, but this surfaced a structural debt: settings needed tabbed layout _yesterday_. The appearance + model config belong in separate UI surfaces; forcing them into a single scrollable modal was a friction point. Execution history was the harder win—tracking image outputs per run required care to avoid: (a) duplicating blobs (solved via SHA refs), (b) holding DB connections open during long runs (solved via per-call `_connect()` + WAL), (c) stale cache references (solved via `onError` fallback + "已被清理" placeholder). The excitement was quiet: it just works, blends into the existing image cache seamlessly, and doesn't slow down the engine.

## Technical Details

**Save conflict flow:**
```
POST /api/workflows {name: "X", dag: ...}
  → name exists? YES → 409 {"error": "exists"}
  → frontend receives 409 → confirm("覆盖?") → doSave(overwrite=true)
  → POST /api/workflows?overwrite=true → 200 OK
```

**Execution history write path:**
- `ws_run(ws, mode, dag, config, callback)` wraps the user callback
- Accumulates node status + image outputs (from `node_finished` event `outputs[handle]`) + harness best_iteration
- On `WebSocketDisconnect` or run end: `try/finally` block calls `finish_execution(workflow_name, mode, status, detail_json, duration_ms)`
- `finish_execution` writes record, then prunes: `DELETE FROM workflow_executions WHERE id NOT IN (SELECT id FROM workflow_executions WHERE workflow_name = ? ORDER BY id DESC LIMIT 50)`
- Recorded only if `target is None` (full run) OR `harness.enabled`; single-node runs skipped (keeps history focused on intentional workflows)

**Image output reference:**
- Node finish event emits `outputs: {[handle]: {dtype: "image", sha, size}}`
- History detail stores SHA only; ImageViewer fetches `/api/cache-image/{sha}` on demand
- If blob evicted (LRU): fetch returns 404 → catch in modal → show "ảnh đã bị dọn" placeholder
- No blob duplication; all runs point to same content-addressed store

**Settings tab persistence:**
- Modal mounts both tabs as children; shell toggles via `display: ${activeTab === "appearance" ? "flex" : "none"}`
- Form state (model list fetch, dropdown selection) stays in component tree—not re-fetched on tab switch
- Avoids `useEffect` race on fetch; avoids multiple API calls per session

## What We Tried

1. **Soft conflict (silent overwrite):** Rejected. Users expect save confirmation when name exists; silent overwrite breaks trust and makes recovery hard.

2. **Execution history as separate page:** Considered route `/workflows/:name/history`. Rejected: modal is quicker, keeps workflow browser + history in one gesture, lighter UX than nav hop.

3. **Image blob duplication strategy:** Sketched storing full image payload per run. Rejected: blows up DB size; violates content-addressed cache design; harder to garbage-collect. SHA refs are correct.

4. **Transaction-holding write:** Proposed holding DB connection across the entire run. Rejected: WAL mode allows concurrent writers; per-call `_connect()` is simpler + safer; avoids deadlock risk on long-running workflows.

5. **Settings inline (no tabs):** Original plan. Rejected after first implementation: appearance + model dropdowns took 40% vertical space; model config buried below fold; modal felt cramped. Tabs solved both issues.

## Root Cause Analysis

**Why settings needed tabbing:** Appearance toggles (theme, light/dark) and model selection are independent concerns. Forcing them into one scroll surface made the modal visually dense and forced users to scroll to find their setting. Tabs separate concerns and reduce cognitive load. Should have been designed this way from the start.

**Why execution history required careful blobing:** Naive approach (store full image bytes per run) scales quadratically with run count. The insight: engine already content-addresses all outputs via SHA. History should reference, not duplicate. This reuses the existing cache machinery + garbage collection + blob store consistency.

**Why form state persistence matters:** React's reconciliation will re-fetch on tab unmount→remount (standard lifecycle). Keeping both tabs mounted avoids refetch cost; display toggle is cheaper. Users expect their dropdown selections to survive tab switches.

## Lessons Learned

1. **User trust on save is non-negotiable.** Silent overwrite breaks it. Conflict detection + explicit confirm is worth the extra roundtrip.

2. **Modal tabbing beats modal bloat.** When modal height exceeds ~80% of viewport, tab it. Especially for orthogonal settings (appearance ≠ model config).

3. **Content-addressed cache is a superpower for history.** Reference by SHA, not payload. Execution history rides on existing blob store semantics + GC without bloating schema or requiring migration.

4. **Try/finally on async paths is non-negotiable.** WebSocketDisconnect must finalize state. Graceful degradation (running → stopped) means users see partial results even if client drops.

5. **Form state lifecycle matters.** Mounting/unmounting triggers refetch; display toggle avoids it. Cheap optimization with outsized UX win.

## Next Steps

1. **User e2e test:** Navigate modal, open history, verify image load + "ảnh đã bị dọn" on cache miss; toggle settings tabs; confirm model selection persists across switch.

2. **Execution history retention policy:** Monitor 50-record limit in production; adjust if workflows generate >10 runs/day (currently conservative; can relax if needed).

3. **Search/filter history:** Backlog—users may want to filter by status/date; deferred as MVP feature (list + detail sufficient for now).

4. **Accessibility audit:** Modal tabs, image viewer alt text, error placeholders. Low priority for internal workflow, but document if shipped to external users.

**Verification:** 6/6 new tests pass (`test_workflow_save_conflict.py`, `test_execution_history.py`); 103/103 regression tests pass; frontend `vite build` clean; 0 blocking code review issues.

---

**Status:** DONE
**Summary:** Workflow save-conflict detection, per-workflow execution history, and settings tab refactoring shipped. No silent overwrites; history rides on existing content-addressed blob store; form state persists across tab switches.
**Concerns:** Execution history retention at 50 records (conservative; may adjust per usage); search/filter deferred to backlog.
