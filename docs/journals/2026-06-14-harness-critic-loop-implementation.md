# Engine Harness Critic-Refine Loop Implementation

**Date**: 2026-06-14 15:50
**Severity**: Medium
**Component**: Engine orchestration, Provider abstraction, Frontend UI
**Status**: Resolved

## What Happened

Shipped engine harness loop for iterative image refinement. Workflows can now run a final product image through an AI vision critic (Gemini), score against user goal, and auto-refine via feedback injection if goal not met — up to iteration limit. Backward-compatible: harness is opt-in via `RunRequest.harness` parameter. Four deliverables:

1. **Harness orchestration layer**: `_run_harness()` wraps DAG execution; locates final product image → critic → conditional loop
2. **Provider critique capability**: `critique_image()` (Gemini vision→JSON score/feedback) + `supports_critique()` detection
3. **Feedback injection mechanism**: Appends AI feedback to gen node's `params["prompt"]` (reuses existing Merkle content-addressing for downstream propagation)
4. **Frontend UI**: Harness config popover + iteration tracker + report panel in App.jsx

Commit ae6a32b. 72/72 backend tests green (10 new harness + 62 regression), frontend build clean, 2 code reviews 0-blocking.

## The Brutal Truth

No major fires this session. Red-team caught two Criticals before code landed (pseudocode doesn't enforce real method signatures); planning discipline paid off. The real win: feedback-as-param-override is so clean it feels like we dodged complexity we didn't know we were carrying. If we'd tried to implement "loop via graph edges" or "dynamic DAG mutation," we'd be neck-deep in cache invalidation hell. Instead: stateless loop, immutable graph, same engine, same cache semantics.

## Technical Details

**Harness loop logic:**
- Runs DAG once (normal execution)
- Critic scores final product image against user goal (vision + JSON critique)
- If score < threshold AND iterations remain: append feedback to gen node's `params["prompt"]` + re-run DAG
- Repeats until goal met OR iteration limit exhausted
- Outputs best iteration + critic report; sink writes ONCE on best result

**Feedback injection:**
- Appends feedback as supplement to existing prompt: `f"{existing_prompt}\n[Critic feedback: {feedback}]"`
- Leverages existing Merkle `node_key` propagation: new prompt hash → new node key → downstream nodes see fresh input
- Avoids `engine_cache_key.py` changes; avoids prune/force hacks
- On mid-loop node failure: keeps best result, exits gracefully

**Provider critic:**
- `critique_image(image_bytes, goal_prompt)` → `{"score": 0–100, "feedback": "..."}`
- Gemini vision model + JSON mode
- `supports_critique()` checks capability before calling (FakeProvider returns False)
- Vision check happens BEFORE generation to fail fast on unsupported providers

**Edit instruction override:**
- `compose_edit_prompt(..., instruction_override=None)` param
- Optional "system instruction" field on edit node (replaces hard-coded "no face swap" identity guard when set)
- Default: None (backward-compatible, uses existing instruction)
- Allows per-workflow customization without hard-coding new rules

## What We Tried

1. **Graph-based loop:** Considered adding cycle edges to DAG (e.g., feedback → gen → product → critic → decision → feedback). Rejected: engine is strictly acyclic; would require cycle detection + cache re-validation logic; orthogonal concern to orchestration.
2. **Loop inside engine:** Proposed adding loop logic to `run_workflow()` directly. Rejected: couples orchestration to engine; harder to test; mixes concerns.
3. **Adaptive prompt module:** Planned `adaptive_prompt.py` helper (override_or_default logic). Rejected: 2 constants → inline param (YAGNI); avoided code_hash staleness trap (code_hash only hashes node CLASS source, not helpers, so moving logic to module wouldn't invalidate downstream cache anyway).
4. **Force/prune cache hack:** Considered invalidating downstream cache on feedback injection. Rejected: feedback-as-param-change already handled via Merkle re-hash; reuses existing cache semantics; cleaner.

## Root Cause Analysis

Planning pseudocode that doesn't trace real method signatures hides type/contract bugs. Red-team forced us to walk the data flow:
- `resolve_model_config()` returns `(config, metadata)` tuple; pseudocode called `.method()` on result (type error)
- `merge_prompt()` concatenates prompts; pseudocode appended feedback without merging (goal duplication)

Lesson: pseudocode → code walkthrough + signature validation BEFORE implementation saves days of debugging.

The feedback-as-param insight came from asking: "What's the simplest mechanism that doesn't require DAG mutation?" Answer: param override. This reuses Merkle key machinery already working for cache, skips cache invalidation logic, and keeps the loop stateless (only state: iteration counter at orchestration level, not in graph).

## Lessons Learned

1. **Engine acyclic constraint is a feature, not a limitation.** Loops live at run-orchestration, not graph edges. Keeps engine simple, cache bulletproof, and logic testable in isolation.

2. **Feedback-as-param-change is the right abstraction.** Avoids touching cache machinery; reuses content-addressed propagation; stateless loop. If we'd chosen graph mutation, we'd be debugging cache staleness for weeks.

3. **Red-team pseudocode walkthrough is non-negotiable.** Forced signature tracing + data-flow check caught two Criticals before code. Planning sketches that don't match real APIs are expensive debt.

4. **YAGNI on adaptive_prompt module was right call.** Keeping override logic inline (2-line conditional in compose_edit_prompt) vs. separate module saved us from code_hash staleness. Modules are cheap; cache key invalidation is not.

5. **Deferred "extract region" node to future milestone.** Doesn't block harness; user wants gradual feature expansion. Shipping smaller + iterating beats planning for hypothetical use cases.

## Next Steps

1. **Manual Gemini e2e verify:** User to run harness with real API key; confirm critic scores + feedback loop works end-to-end (pending on user's side).
2. **Monitor critic performance:** Log score distributions + feedback quality. If critic is too harsh/lenient, fine-tune system prompt.
3. **Generic region-extract node:** Plan as separate milestone (depends on UI for region selection, not critical path).
4. **Hardened loop invariants:** Document in `_run_harness()` docstring: acyclic graph, stateless loop, Merkle propagation semantics.

**Verification:** 72/72 tests (10 harness + 62 regression), frontend vite build OK, 2 code reviews DONE, git status clean post-commit ae6a32b.

---

**Status:** DONE
**Summary:** Engine harness loop shipped with clean feedback injection (param-based, Merkle-aware) and provider critique capability. Acyclic graph design avoided cache complexity. Red-team pseudocode walkthrough caught Criticals early. Tests all green.
**Concerns:** Manual e2e pending (user to run with real Gemini key); deferred generic region-extract node (acceptable for MVP).
