# Per-Node Run + Auto-Cache Implementation Complete

**Date**: 2026-06-13 12:05
**Severity**: Medium
**Component**: Engine cache, WebSocket protocol, Frontend UI, Provider abstraction
**Status**: Resolved

## What Happened

Shipped per-node execution + transparent auto-cache (n8n-style) + fake provider offline mode. Workflows now re-use disk-cached node outputs on re-run instead of re-calling paid AI providers (gemini, openai). Full backward-compatible — existing code paths untouched.

Four phases landed:
1. **Engine cache**: Content-addressed storage with Merkle key propagation
2. **WebSocket protocol**: Run envelope with `target`/`force` directives
3. **Frontend**: Per-node ▶ run-to-here, ⚡ cache status badge, 🗑 clear-cache button
4. **Offline fake provider**: FakeProvider + CLI for testing without network

## The Brutal Truth

This feature is solid overall, but we made a **cache invalidation trap** that only works because of luck. If someone adds a "force full re-run without specifying node target" path, the cache will silently return stale outputs to downstream nodes. It's documented now, but it's the kind of time-bomb that bites hard at 3am when someone refactors the run logic and forgets the invariant.

The stale-cache-on-model-edit issue is a conscious design trade-off, but it's non-obvious. Users will edit a named provider's model, re-run, get cached results, and swear the change didn't work. Clear-cache UX is the band-aid.

## Technical Details

**Engine cache (Phase 1):**
- `node_key = sha256(type + resolved_params + parent_output_keys + code_hash(class source))`
- Disk structure: `cache/nodes/{key}.json` (manifest) + `cache/blobs/{sha}.bin` (dedupe blobs)
- LRU eviction by mtime when blobs exceed CACHE_MAX_BYTES (default 500MB)
- `run_workflow` with `target` (run node + ancestors) + `force_ids` (bypass cache)
- Cache HIT skips `instance.run()` entirely → zero provider calls

**WS protocol (Phase 2):**
- `/ws/run` accepts `{workflow, target, force}` envelope OR plain workflow (backward-compat)
- `RunEvent.cached` flag signals cache hit to frontend
- `POST /api/cache/clear` for manual eviction

**Frontend (Phase 3):**
- `RunContext` state management for target/force tracking
- Per-node ▶ button triggers `startRun({target, force})`
- ⚡ badge on cached nodes
- 🗑 Toolbar button for full cache clear

**Fake provider (Phase 4):**
- `FakeProvider`: offline PNG placeholder + echo text, zero network deps
- `FORCE_FAKE` global for testing
- `run_node.py` CLI: run single node offline
- Windows UTF-8 fix: `sys.stdout.reconfigure(encoding="utf-8")` for Vietnamese console output

## What We Tried

1. **Initial approach:** Hash entire resolved_params (including api_keys). Rejected: cache would be useless on key rotation or config migration. Switched to hashing config NAME only (stable identifier).
2. **Eviction strategy:** LRU by mtime (simple, effective). Considered size-weight (YAGNI'd — manifest bytes negligible).
3. **Force semantics:** Debated whether `force` should invalidate node_key. Decided: no, force only controls re-run decision. Parent cache chain still valid. Works only because ▶ path always prunes downstream.

## Root Cause Analysis

The cache trap exists because we conflated two concerns:
- **Cache key** (content identity) should be immutable and reflect true inputs
- **Cache bypass** (re-run decision) is a UI intent, orthogonal to identity

Forcing re-run of node A doesn't change A's content hash, so if a child B has identical params and wasn't forced, it cache-hits B's manifest (which still points to A's old output). The only reason this doesn't corrupt the workflow is the ▶ "run-to-here" path always sends `target=A` + `force=[A]`, which prunes B from the run entirely. No downstream = no stale hit. But that's fragile. A future dev might add `force_full_rerun()` without re-reading the cache invariant.

The model-edit staleness is intentional (per planning interview), but it's a hidden gotcha. node_key uses config NAME, not resolved model string. Users expect editing config to invalidate cache. We accept this leak in exchange for cache surviving key/credentials rotations.

## Lessons Learned

1. **Invariants must live in docstrings, not architecture.** The "force implies target pruning downstream" rule is now explicit in `run_workflow` docstring. If that function ever gets refactored, the comment is the speed bump. Build linters that flag removals of multi-line docstrings in critical functions.

2. **Cache key design is not symmetrical.** What's in the key (stable config name) ≠ what the user thinks changed (active model). This asymmetry saved us from key rotation thrashing, but it's confusing. Document trade-offs in code, test that clear-cache actually works, and surface the "model edit = manual clear" requirement in UI help text.

3. **Windows CLI encoding is a silent killer.** `run_node.py` crashed on Vietnamese text under cp1252 console. This only surfaced in offline test flow. Test non-ASCII output on target platforms early — don't wait for QA in a non-Latin locale.

4. **YAGNI on eviction weight was right call.** We evict blob bytes only (manifests free). If manifests ever grow, revisit. For now: ship simple, measure, extend on data.

## Next Steps

1. **Hardened docstring audit:** Review `run_workflow`, `_traverse_cache_path`, `CacheManager` for invisible invariants. Pin them in docstrings with examples.
2. **Test "force full re-run" path if it ever lands:** If we add a `force_all=True` mode, that test MUST verify downstream nodes are NOT cache-hit.
3. **UI nudge for model edits:** Add a tooltip on the provider config panel: "Edit model / API key? Clear cache for new outputs." (Lower priority, nice-to-have.)
4. **Monitor cache hit rates in production:** Log cache hit/miss ratio per workflow. If hit rate > 90%, we're winning; if < 30%, investigate whether key design is too tight.

**Verification:** Offline test suite 9/9 + 6/6 + 9/9 (no regression), WS integration PASS, E2E backward-compat PASS, `vite build` OK, engine.py 160 LOC. Code review DONE_WITH_CONCERNS, zero blockers. No git repo, so no CI to gate.

---

**Status:** DONE
**Summary:** Per-node cache + offline fake provider shipped with backward-compat intact. One architectural trap documented (force ≠ invalidation), one accepted gotcha (model edits don't clear cache). Tests pass. Ready for integration.
**Concerns:** Invariant-in-docstring fragility; stale-cache UX leak on model edit (accepted trade-off).
