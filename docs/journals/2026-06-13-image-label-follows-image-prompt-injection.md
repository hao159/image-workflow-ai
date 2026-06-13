# Image Description Follows Image → Auto-Injected Reference Block

**Date**: 2026-06-13 15:30
**Severity**: Low
**Component**: Node params, Engine label propagation, Cache key, Frontend node UI
**Status**: Resolved (code) / live-verify pending

## What Happened

Added a "Mô tả ảnh" (image description) field to source nodes (`load_image`, `generate_image`). Description does double duty: (a) renders as a node subtitle for naming, (b) **follows the image** downstream so `edit_image` auto-prepends a numbered reference block (`Ảnh đầu vào:\n- Ảnh 1: …\n- Ảnh 2: …`) before the user prompt — AI now knows which input image is which in multi-image composites.

Three phases, `--tdd` (tests written red first):
1. **Backend param + pure helper**: `Param.is_image_label` flag; `image_label_block.py` (build block + compose prompt).
2. **Engine label propagation + cache**: labels travel with images; cache invariant preserved.
3. **Frontend subtitle + docs**: `.wf-node-subtitle` band; README + memory.

## The Brutal Truth

The whole feature rests on **AI actually respecting "Ảnh 1/Ảnh 2"** — that's an unverified assumption until someone runs a real Gemini multi-image job. Every test here proves the *plumbing* (label reaches the prompt correctly), not the *outcome* (AI maps Ảnh 1 → right object). If Gemini ignores the numbering, the architecture is fine but the UX promise is hollow. Mitigation is wording-only (`image_label_block.py`), but the risk is real and lives outside the test suite.

## Technical Details

**Cache invariant (the crux):**
- Label param is **excluded** from `node_key` (`key_params_excluding_labels` + `label_params` in `engine_cache_key.py`) → editing a description does NOT regenerate the AI image (no token cost).
- Label hash IS appended to the image's `output_key` (`label_out_key` → `{base}#{sha8}`) → downstream `edit_image` sees a changed `in_key` → re-runs with the new prompt.
- Engine writes the `labels` map on **both** the cache-hit branch and the run branch — so a cache-hit source still propagates its label. This is the single most forgettable line and it's explicitly tested.

**Label flow (engine.py run loop):**
- Gather labels per-edge alongside values/in_keys (same iteration → guaranteed length/order alignment).
- `out_label` = own param (load/generate) > passthrough from input port (transform nodes) > "" (edit_image composite).
- `instance.input_labels = {handle: [labels]}` set before `run`. `edit.py` builds labels in image order `[image, *images, image2]` to match the numbering.

**Passthrough:** `BaseNode.label_passthrough_from="image"` on resize/filter/adjust → label survives transforms. `edit_image` does not declare it → composite output carries no label.

## What We Tried

1. **Where to put the description in node_key:** excluded entirely. Alternative (include + special-case downstream) rejected — excluding is simpler and the out_key hash already propagates change downstream.
2. **Reference block placement:** before prompt, list-only (no instruction sentence) — per brainstorm decision, to avoid biasing the model.
3. **Vietnamese vs English header:** kept Vietnamese (`Ảnh đầu vào:`); switch to English only if live verify shows AI drift.

## Lessons Learned

1. **Test plumbing ≠ test outcome.** Strong unit/integration coverage of label propagation gives false confidence about the AI behavior it enables. Separate "data arrives correctly" from "AI does the right thing" — the latter needs a live check, flagged explicitly as a TODO rather than buried.
2. **Cache asymmetry is reusable.** Same trick as the prior per-node-cache work: keep an input out of the identity key but let it perturb the *output* key. Editing description = cheap downstream re-run, zero regeneration. Documented in README cache section.
3. **Closure-in-loop is fine when invoked same-iteration.** `record_outputs` defined inside the run loop drew a review flag; confirmed safe (called before next rebind). Worth a one-line comment to pre-empt the question.

## Next Steps

1. **Live Gemini multi-image verify (user, blocking real use):** 2× `Tải ảnh lên` ("cái áo" / "người mẫu") → `Sửa ảnh` (Gemini) "mặc áo ở Ảnh 1 lên người ở Ảnh 2". Confirm composite maps correct objects; confirm prompt contains the block via `CODEX_DEBUG`/log. If AI drifts → tune wording in `image_label_block.py` only.
2. **(Out of scope) Port-side `Ảnh N` badge:** show numbering at the edit node's input ports so users don't guess edge order.

**Verification:** `test_nodes.py` 16/16 (8 new), `test_engine_labels.py` 7/7 (new), regression `test_engine_cache.py` 9/9 + `test_codex.py` 19/19, `import app.nodes` OK, `vite build` clean (201 modules). Code review DONE, 0 blocking (3 Low/cosmetic notes left per YAGNI). Not a git repo → no commit/CI.

---

**Status:** DONE
**Summary:** Image description now follows the image into a numbered reference block in `edit_image`, with the cache invariant (no AI regen on description edit, but downstream re-runs) implemented and explicitly tested. Backward-compatible: no labels → prompt unchanged.
**Concerns:** Core UX assumption (AI honors "Ảnh 1/2") unverified until a live Gemini run; mitigation is wording-only and isolated.

---

## Update — 17:30: live Codex run confirmed the predicted failure → interleaving fix

Ran live on **ChatGPT Codex** (`gpt-image-2-codex`): frame + 6 faces → poster. **Names correct, faces swapped** (Top 3 slot "Nguyễn Chánh Phương" got a different person's face). Exactly the unverified-assumption risk flagged above, materialized.

**Self-checked the debug log** (`logs/codex/260613-170152-ab964a.log`) instead of trusting memory: the app sent the reference block + all 7 images **in correct order**. So the app is faithful — the "hallucination" is the *image model* mismatching identity, not a code bug. (Worth stating plainly: when a user suspects hallucination, read the actual request log before defending the code.)

**Root cause:** a detached text list ("Ảnh 1: …, Ảnh 2: …") followed by N bare image attachments forces the model to *infer* positional binding (3rd attachment = Ảnh 3). With 6 faces, gpt-image doesn't hold that binding.

**Fix (app-layer, the right lever):** interleave the caption immediately before its image. Codex (`openai_codex.py`) and Gemini (`gemini.py`) — both support mixed text+image content — now emit `input_text "Ảnh N: <name>"` directly before each `input_image`. New shared helper `numbered_image_caption` in `providers/base.py`. Node `edit.py` passes `image_labels` (parallel to `images`) via `**options`; OpenAI Images-Edit / ComfyUI / Fake ignore it (no mixed-content support) and keep the text-block behavior — fully backward-compatible. Added `IMAGE_REF_INSTRUCTION` ("keep each person's identity, do not swap faces") to `compose_edit_prompt` when labels exist.

**Honest ceiling:** interleaving raises the odds the model binds face→slot correctly; it does **not** guarantee it. Compositing many real faces in one generative call is inherently unreliable. The only deterministic fix is PIL-pasting faces into fixed slot coordinates — a different feature requiring frames with known coordinates, out of scope.

**Verification:** `test_codex.py` 23/23 (+4: Codex interleave, Gemini interleave, caption helper, no-label bare-images), `test_engine_labels.py` 9/9 (+2: labels passed in order, identity instruction present), `test_nodes.py` 16/16, `test_engine_cache.py` 9/9. Imports clean. Live re-verify on Codex/Gemini still pending user.
