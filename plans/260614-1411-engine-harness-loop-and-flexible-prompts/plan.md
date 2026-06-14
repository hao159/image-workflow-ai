---
title: 'Biến app thành Harness: engine critic-refine loop + prompt linh hoạt'
description: >-
  App vận hành như harness: engine bọc DAG trong vòng critic-refine có limit
  (opt-in trước → mặc định sau). Critic AI vision tự chấm output vs goal (auto =
  prompt node sinh cuối) + tiêu chí tùy chọn; hết limit → xuất best + report.
  Thêm node trích vùng tổng quát (mô tả gì tách nấy → bbox → crop PIL). Bỏ chỉ
  thị prompt cứng → builder theo intent + override đè.
status: completed
priority: P2
branch: main
tags:
  - harness
  - engine
  - prompt
  - image-workflow
blockedBy: []
blocks: []
created: '2026-06-14T07:30:07.726Z'
createdBy: 'ck:plan'
source: skill
---

# Biến app thành Harness: engine critic-refine loop + prompt linh hoạt

## Overview

App hiện là **DAG một-pass**. Mục tiêu: cho nó vận hành như **harness** — engine bọc run trong **vòng critic-refine có limit**: chạy → AI critic chấm output vs goal → chưa đạt thì inject feedback, re-run → lặp tới khi đạt hoặc hết limit → xuất **iteration tốt nhất + report**.

Kèm 2 thứ gỡ bug gốc rễ:
- **Node trích vùng tổng quát** (mô tả gì tách nấy: mặt/bò/chó/áo) → vision trả bbox → crop PIL (giữ pixel gốc). Pre-process độ tin cậy cho ghép ảnh.
- **Prompt linh hoạt**: bỏ chỉ thị cứng auto-chèn (`IMAGE_REF_INSTRUCTION`) → builder theo intent; **giữ auto-default nhưng cho override đè**.

Nguồn brainstorm (đã chốt): `plans/reports/brainstorm-260614-1411-engine-harness-loop-and-flexible-prompts-report.md`.

**Mode:** `--tdd` — mỗi phase viết test khóa hành vi (đặc biệt **backward-compat**) TRƯỚC khi sửa code.

## Mấu chốt kiến trúc (verified qua đọc code)

1. **Engine acyclic** (`engine.py:49` chặn cycle) → loop KHÔNG ở dây nối, mà ở **tầng run-orchestration** (engine bọc ngoài DAG).
2. **Feedback = APPEND vào `params["prompt"]` (supplement, KHÔNG replace)** → `merge_prompt` đặt feedback SAU prompt cổng (đúng ngữ nghĩa "thêm chỉnh sửa", tránh nhân đôi/bỏ qua prompt từ cổng — red-team C3). Param đổi → `node_key` đổi → node sinh + downstream re-run, nhánh khác cache-hit. **KHÔNG đụng `engine_cache_key.py`**. **Goal cho critic = prompt đã merge** (engine tự gọi `merge_prompt` trên input đã resolve), KHÔNG đọc param thô.
3. **Backward-compat = success criteria cứng**: harness là **opt-in** qua field `harness` trong `RunRequest`. Thiếu field → `run_workflow` chạy đúng đường hiện tại (mọi test cũ phải xanh).
4. **Provider capability** mở rộng theo pattern sẵn có (`generate_text` mặc định raise ở `base.py`): thêm `detect_region` (node trích) + `critique_image` (critic). Gemini implement; provider khác inherit default raise → báo lỗi rõ "harness cần provider vision".

## Phases

> Re-scope sau red-team: node trích vùng tách sang milestone riêng (không block harness). Thứ tự mới: prompt override → engine loop → frontend.

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Prompt override đè (inline)](./phase-01-adaptive-system-prompt.md) | Completed |
| 2 | [Engine harness loop opt-in (critic-refine)](./phase-02-node-tr-ch-v-ng-t-ng-qu-t.md) | Completed |
| 3 | [Frontend harness UI + docs](./phase-03-engine-harness-loop-opt-in.md) | Completed |
| 4 | [Node trích vùng tổng quát (extract_region)](./phase-04-frontend-harness-ui-v-docs.md) | Completed (sau harness) |

## Decisions (chốt từ brainstorm)

- Kiến trúc: **engine-level harness loop** (hướng A), KHÔNG chỉ "thêm node".
- Rollout: **opt-in toggle trước** → mặc định sau khi đo chất lượng.
- Critic: **AI vision tự chấm** vs goal + ô tiêu chí tùy chọn (trống → chấm theo goal).
- Goal: **tự động = prompt của node sinh ảnh terminal** (không bắt user nhập thêm).
- Hết limit chưa đạt: **xuất iteration điểm cao nhất + report** (không giết workflow).
- Chỉ thị cứng "không tráo mặt": **giữ auto-default + override đè**.
- Node trích: **TỔNG QUÁT** (mô tả → bbox → crop PIL), KHÔNG đặc trị "mặt".

## Dependencies

- Build lên plan đã `completed` `260613-1430-image-node-description-prompt-injection` (tạo `image_label_block.py`, `numbered_image_caption`, label flow). Phase 1 **sửa** chính file đó (làm `IMAGE_REF_INSTRUCTION` override-able). Không block (đã xong) — chỉ kế thừa + tinh chỉnh.
- Không có plan unfinished nào overlap → không cần `blockedBy`/`blocks`.

## Key files (paths đã sửa theo red-team C1 — đều ở `backend/app/nodes/`, KHÔNG ở app root)

**Phase 1 (prompt override, inline):**
- `backend/app/nodes/image_label_block.py` — `compose_edit_prompt` nhận `instruction_override`; default giữ nguyên (backward compat). KHÔNG tạo module mới.
- `backend/app/nodes/edit.py` — thêm param "Chỉ thị hệ thống (tùy chọn)" → truyền override.
- (`enhance_prompt.py` KHÔNG đụng; `adaptive_prompt.py` KHÔNG tạo — bỏ theo Scope F1-F3.)

**Phase 2 (engine harness loop):**
- `backend/app/engine.py` — tách `_execute_pass` (state tươi mỗi lần) + harness branch + locate_product + effective_prompt (dùng `nodes/prompt_merge.merge_prompt`) + run_sinks_once.
- `backend/app/models.py` — `HarnessConfig`, `RunRequest.harness`, `RunEvent` thêm field iteration/score/report + type `harness_iteration`/`harness_report`.
- `backend/app/main.py` — ws/run đọc `harness`, truyền vào `run_workflow`, guard emit khi WS đóng.
- `backend/app/providers/base.py` — `critique_image` default raise.
- `backend/app/providers/gemini.py` — `critique_image` (vision text + JSON; UNPACK `provider,model`).
- `backend/app/providers/fake.py` — `critique_image` điểm theo iteration (test).

**Phase 3 (frontend):**
- `frontend/src/App.jsx` (~563 dòng — nút Chạy `:456`, WS switch `:302-340`, reset `:288-292`); `frontend/src/RunContext.jsx` (stub). Không có Toolbar/store riêng (C11).

**Test:** `backend/test_nodes.py` (override), `backend/test_harness_loop.py` (mới), regression toàn bộ.

**Docs:** `README.md` (mục harness), memory project.

**Phase 4 (HOÃN):** `backend/app/nodes/extract_region.py` + `detect_region` (gemini/base/fake) — milestone riêng.

## Red Team Review

### Session — 2026-06-14
**Reviewers:** 3 (Failure Mode Analyst, Assumption Destroyer, Scope & Complexity Critic)
**Findings:** 26 raw → ~22 dedup, tất cả có `file:line` (qua evidence filter).
**Severity:** 2 Critical, 8 High, ~12 Medium.
**Disposition:** 13 correctness Accept-applied; 5 scope-simplify Accept; 1 scope giữ (user decision sticky); 2 deferred (extract_region milestone).

| # | Finding | Sev | Disposition | Applied |
|---|---|---|---|---|
| C1 | File paths sai (nodes/ chứ không app root) | High | Accept | Key files + phases |
| C2 | `resolve_model_config` trả tuple, pseudocode gọi method trên tuple | Critical | Accept | Phase 2 + 4 |
| C3 | Inject prompt bỏ qua cổng nối; merge concat → goal nhân đôi | Critical | Accept | Phase 2 (append supplement + goal từ merge) |
| C4 | Critic chấm ảnh thô node sinh, không phải sản phẩm cuối (post-transform) | High | Accept | Phase 2 |
| C5 | Fail giữa loop → mất best, không report | Critical→High | Accept | Phase 2 (recovery) |
| C6 | `save_image` ghi N file; on-disk last ≠ best | High | Accept | Phase 2 (sink 1 lần trên best) |
| C7 | locate_terminal underspecified (0 node sinh crash; multi-sink theo node-id sort) | High | Accept | Phase 2 (run_error rõ) |
| C8 | Critic buộc dùng provider node sinh; non-vision generator chết | High | Accept | Phase 2 (critic provider riêng + check trước) |
| C9 | Gemini cần image-in→JSON-out; wrapper hiện không có path | Medium | Accept | Phase 2 + 4 (vision text + json mime) |
| C10 | `code_hash` hash class source → move logic ra module không vô hiệu cache | High | Accept | Giải bằng S1 (không tạo module) |
| C11 | Frontend không modular — 1 `App.jsx` ~563 dòng | High | Accept | Phase 3 (file thật) |
| C12 | WS disconnect mất best RAM; feedback non-deterministic | High | Accept | Phase 2 (document, no resume MVP) |
| C13 | Feedback reassign không tích lũy → dao động | Medium | Accept | Phase 2 (accumulate cap) |
| S1 | `adaptive_prompt.py` over-abstraction (override or default) | High | Accept | Phase 1 (inline param) |
| S2 | Move enhance SYSTEM_INSTRUCTION = churn | Medium | Accept | Phase 1 (không đụng enhance) |
| S3 | "Phase 1 nền cho critic" = fictional reuse | High | Accept | Phase 1/2 (bỏ justification) |
| S4 | `_run_pass` override-dict over-built | High | Accept | Phase 2 (`_execute_pass` tối thiểu, không override-dict tổng quát) |
| S5 | best-selection + history gold-plating | Medium | **Reject** | User đã chốt "best + report" ở brainstorm — sticky; chỉ rút gọn payload |
| S7 | extract_region `provider` select 1 giá trị hợp lệ = footgun | Medium | Accept | Phase 4 (bỏ select MVP) |
| S8 | extract_region không block harness — tách | Medium | Accept | Tách Phase 4 → milestone riêng |
| S9 | param instruction có thể quá ý user | Medium | Accept (partial) | Phase 1 (giữ override theo user, chốt cache rỗng=re-run 1 lần) |

**Rejected:** S5 (best+report) — user đã chọn rõ trong brainstorm; không tự đảo (review-audit-self-decision rule 3). Chỉ đơn giản hóa payload report, giữ best-selection.

### Whole-Plan Consistency Sweep
- Đọc lại plan.md + 4 phase sau khi áp finding.
- Sửa stale: paths app-root→`nodes/`; bỏ mọi nhắc `adaptive_prompt.py` (Key files, Phase 1, Phase 2 critic justification); inject "replace"→"append supplement"; Phase 2/3/4 đổi tiêu đề + nội dung theo re-scope; "node trích tự sinh form" gỡ khỏi Phase 3 (đã tách).
- Đối chiếu: Phase 2 dùng `merge_prompt` (nguồn `nodes/prompt_merge.py`) ↔ Mấu chốt #2 ↔ Key files — nhất quán. Phase deps: 1→2→3; 4 deferred (deps []).
- **Filenames vs titles:** file `phase-02-node-tr-ch-...md` nay chứa Engine; `phase-03-engine-...md` nay chứa Frontend; `phase-04-frontend-...md` nay chứa Extract-deferred (đổi nội dung, không đổi tên file — link trong bảng Phases trỏ đúng file + nhãn mới). Không gây mâu thuẫn nội dung.
- **0 mâu thuẫn còn lại.** Plan sẵn sàng implement (Phase 1-3); Phase 4 hoãn.
