# Code Review — per-node run + auto-cache + fake provider

Reviewer: code-reviewer | Date: 2026-06-13 | Mode: plan-execution review (report only, no edits)

## Scope
- NEW: cache.py, engine_cache_key.py, providers/fake.py, run_node.py, test_engine_cache.py, test_ws_cache.py, test_fake_provider.py, RunContext.jsx
- MOD: engine.py, config.py, models.py, main.py, providers/__init__.py, App.jsx, api.js, WorkflowNode.jsx, workflow-node.css
- Backend LOC: engine 154, cache 117, engine_cache_key 65, providers/__init__ 56, fake 57, run_node 77 — all < 200 (rule OK)

## Verification run (offline)
- test_engine_cache.py → 9/9 PASS
- test_fake_provider.py → 6/6 PASS
- test_nodes.py (regression) → 9/9 PASS
- test_ws_cache.py / test_e2e.py need running backend — controller already verified passing
- `cache/` present in root `.gitignore` (line 7) — OK

## Overall Assessment
Solid, well-scoped implementation. Merkle key-propagation correct; cache hit truly skips `instance.run` (verified by call-count test). Backward-compat WS preserved. Error boundaries reasonable, no secret/PII leak introduced, no auth surface changed. Code is clean, commented, modular. No blocking defects found.

## Critical Issues
None.

## High Priority
None blocking. See "Correctness notes" below for two accepted-by-design behaviors worth confirming.

## Correctness notes (verified against code + plan)

### C1 — force on a node does NOT propagate fresh output downstream (BY DESIGN, no live bug)
engine.py:127-148. A forced node re-runs and gets new bytes, but its `out_keys` value is `f"{nk}:{handle}"` where `nk` = node_key(type, params, in_keys, code) is **unchanged** (force doesn't alter the key). So a downstream child sees identical `in_keys` → same key → **cache-HIT**, i.e. children keep stale output even though the forced parent produced a new image.
- Why not a live bug: the only force path is frontend `runNode` → `startRun({target:id, force:[id]})` (App.jsx:357). `target` prunes everything downstream of the node out of `order` (prune_to_ancestors), so a forced node never has an executed child in the same run.
- Risk: if a future caller ever passes `force` WITHOUT a matching `target` (e.g. CLI / API / "force full re-run"), downstream will silently NOT see the regenerated image. Recommend a one-line guard or doc note on `run_workflow`: "force without target only refreshes the forced node itself; downstream stays cache-hit since key is content-address not run-identity." Matches plan interview Q1 intent but the constraint (force⇒target) is implicit, not enforced.

### C2 — model-config mutation behind a stable config name = stale cache (ACCEPTED)
node_key hashes `params["provider"]` = the config NAME string (generate.py:30, edit.py, enhance_prompt.py), not the resolved api_key/model/base_url. Editing a named config's underlying model in ⚙ Settings does NOT invalidate cache → re-run serves old image.
- Explicitly accepted in plan Validation Log interview Q4 ("chấp nhận stale; key theo params"). User remedy = 🗑 Xóa cache. No action needed; flagging so it's a conscious sign-off, not a surprise at demo.

### C3 — node_started emitted before cache check (ACCEPTABLE)
engine.py:125 emits `node_started` (UI flips node to status=running) then immediately `node_finished` with `cached=true` on hit. Brief running→done flash on cache-hit. Harmless; frontend handles both events in order. Matches plan's "acceptable flash" note.

## Medium Priority

### M1 — `_evict_if_needed` evicts blobs but never prunes orphaned manifests
cache.py:95-117 deletes oldest blobs; the manifests pointing at them remain on disk. `load()` correctly returns None for an orphan manifest (cache.py:57-58, tested), so behavior is safe — but `nodes/*.json` accumulate unbounded and are never counted toward `CACHE_MAX_BYTES` (only `blobs/*.bin` are summed, line 100). For text-only nodes the manifest is the only artifact and is never evicted at all. Low real impact (manifests tiny), but the "total never exceeds CACHE_MAX_BYTES" guarantee (acceptance #3) holds only for blob bytes, not total cache footprint. Acceptable for YAGNI; note the limitation.

### M2 — `os.utime` LRU touch only refreshes blobs, not manifests
cache.py:61. LRU "youthening" on read touches the blob mtime, so a frequently-read image survives eviction — good. But two manifests sharing one deduped blob both rely on that single blob's mtime; evicting the blob orphans BOTH manifests at once. Edge case only under dedupe + tight cache; acceptable.

### M3 — `make_provider` requires `api_key` kwarg by class but fake/codex bypass it
providers/__init__.py:27-33 — verified `make_provider("fake")` returns `FakeProvider()` with no api_key (no crash), codex `cls()`, comfyui `base_url`, else `api_key=`. FakeProvider.__init__ inherited from ImageProvider takes no required args — confirmed no kwarg crash. OK.

## Low Priority

### L1 — fake.py mutable-ish default & PIL aspect rounding
fake.py:34 `base: bytes = None` should be `Optional[bytes]` for type-cleanliness (cosmetic). `_size` clamps with max(1,...) — safe against 0-division. Fine.

### L2 — run_node.py bypasses cache & engine entirely
run_node.py:62-63 calls `cls().run(...)` directly — no caching, no event emit. Intentional (offline single-node test). But it does NOT exercise `resolve_params` merge with provider resolution edge cases the engine path has (e.g. multi-port gather). Fine for its stated purpose; just not a substitute for engine coverage.

### L3 — main.py envelope-vs-plain disambiguation
main.py:187 `"workflow" in data` distinguishes envelope from plain Workflow. Verified Workflow model (models.py:21-25) has only name/nodes/edges — cannot legitimately contain a top-level "workflow" key, so no false-positive. `json.loads` raises `JSONDecodeError` (a `ValueError` subclass) → caught by `except (ValidationError, ValueError)` at line 192. Correct. Robust.

## Edge cases checked (no defect)
- Parent pruned out by `target` feeding a surviving child: prune_to_ancestors keeps ALL ancestors of target (engine_cache_key.py:47-65, BFS over parents), so a surviving node never has a missing parent in `order`. `incoming`/`results` lookups guarded by `if src in results` (engine.py:112). Safe.
- Cycle → `_topo_order` raises ValueError → emitted as run_error, no crash (engine.py:82-85).
- Eviction reads module globals dynamically (cache.py:24-25 module-level rebind + functions read `CACHE_DIR`/`CACHE_MAX_BYTES` at call time) — test reassignment works, confirmed by passing test_evict_over_limit.
- Preview failure isolated (`_make_preview_safe` swallows, returns None) — won't kill run (engine.py:61-69).
- WS plain-workflow path still runs full (test_ws_cache step 5 + test_e2e) — backward-compat intact.
- Frontend: single `running` flag gates both toolbar ▶ and per-node ▶ (WorkflowNode.jsx:67 `disabled={running}`); no duplicate socket logic (one `openRunSocket` in startRun). Full-run resets all nodes then restores cache-hit preview via node_finished event — the intended (accepted) flash.

## Positive Observations
- Call-count test (`_CountNode.calls`) is the right way to prove cache-hit skips execution — strong test design.
- Orphan-manifest-as-miss is handled AND explicitly tested (test_evict_over_limit tail).
- `code_hash` gracefully degrades to "" for dynamically-defined classes (engine_cache_key.py:27-30) — keeps test nodes deterministic.
- WS error handling distinguishes WebSocketDisconnect from engine errors; `ws.close()` RuntimeError swallowed in finally (main.py:209-213).
- Frontend onclose detects mid-run backend drop and surfaces a clear message instead of hanging (App.jsx:337-350) — good UX under uvicorn --reload.

## Acceptance criteria verdict
1. Deterministic key + Merkle downstream invalidation — VERIFIED (tests + code)
2. Cache HIT skips instance.run; force re-runs; target prunes — VERIFIED
3. Auto-trim ≤ CACHE_MAX_BYTES (blobs only — see M1); oldest-mtime first; evicted-blob load→None — VERIFIED
4. WS backward-compat plain workflow — VERIFIED
5. No regression (test_nodes 9/9; e2e per controller) — VERIFIED
6. Real providers unaffected when FORCE_FAKE=False — VERIFIED (resolve_model_config reads FORCE_FAKE at call-time, else normal db path)
7. engine.py < 200 (154); new files reasonable — VERIFIED

## Unresolved questions
1. Should `run_workflow` enforce/warn that `force` without `target` won't refresh downstream (C1)? Currently safe only because the sole caller pairs them. Recommend a doc comment or assert if a force-only path is ever added.
2. M1: is unbounded manifest growth (esp. text-only nodes never evicted) acceptable long-term, or should a future pass count + prune `nodes/*.json`? YAGNI for now.
