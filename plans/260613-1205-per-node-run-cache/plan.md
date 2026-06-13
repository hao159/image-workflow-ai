---
title: "Per-node run + auto-cache (kiểu n8n) + fake provider"
description: "Chạy lại chỉ node đã đổi, tái dùng output cache trên đĩa → không gọi lại API AI tốn token. Nút ▶ trên từng node + fake provider + CLI run-node để test node offline."
status: completed
priority: P2
branch: ""
tags: [engine, cache, frontend, dx, testing]
blockedBy: []
blocks: []
created: "2026-06-13T05:22:28.756Z"
createdBy: "ck:plan"
source: skill
---

# Per-node run + auto-cache (kiểu n8n) + fake provider

## Overview

Mỗi lần thêm/sửa node rồi "▶ Chạy" hiện chạy lại CẢ workflow → gọi lại hết provider AI trả phí ở thượng nguồn → tốn token. Giải pháp: **memoization địa chỉ-nội-dung** trong engine — mỗi node có `node_key = sha256(type + resolved_params + parent_output_keys + code_hash)`; key trùng cache (trên đĩa) → bỏ qua thực thi, dùng lại output (KHÔNG gọi API). Đổi gì → key đổi lan xuống → node đó + downstream chạy lại; còn lại cache-hit. Bổ sung **nút ▶ trên từng node** (chạy tới node đó), **fake provider** + **CLI run-node** để test code node offline (kịch bản C).

Thiết kế gốc (đã user duyệt): `plans/reports/brainstorm-260613-1205-per-node-run-cache-design-report.md`

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Engine memoization + cache](./phase-01-engine-memoization-cache.md) | Done |
| 2 | [WS protocol target/force](./phase-02-ws-protocol-target-force.md) | Done |
| 3 | [Frontend per-node run + cache UI](./phase-03-frontend-per-node-run-cache-ui.md) | Done |
| 4 | [Fake provider + run-node CLI](./phase-04-fake-provider-run-node-cli.md) | Done |

## Completion (2026-06-13)

Triển khai xong cả 4 phase. Test offline: `test_engine_cache.py` 9/9, `test_fake_provider.py` 6/6, `test_nodes.py` 9/9 (không regression). Cần backend chạy: `test_ws_cache.py` PASS, `test_e2e.py` PASS (backward-compat full-run giữ nguyên). Frontend `vite build` OK (199 modules). `engine.py` 160 dòng (<200). Code review: DONE_WITH_CONCERNS, 0 lỗi chặn — báo cáo `plans/reports/from-code-reviewer-to-cook-per-node-cache-review-report.md`.

Bất biến đã chốt (ghi trong docstring `run_workflow`): force KHÔNG đổi node_key → muốn downstream thấy output mới phải dùng `target` (prune) hoặc đổi param; nút ▶ đã gửi target+force nên an toàn. Stale khi sửa model sau lưng config-name: chấp nhận (remedy = 🗑 Xóa cache). Eviction chỉ tính bytes `blobs/`, manifest text nhỏ không trim (YAGNI).

## Key decisions (đã chốt)

- Cache key: **Merkle / key-propagation** (không hash lại bytes ảnh). Có `code_hash = sha256(inspect.getsource(cls))` → sửa code node là cache tự vô hiệu.
- Cache lưu **trên đĩa** `ROOT_DIR/cache/` (sống qua `--reload`). `nodes/{key}.json` (manifest + preview inline) + `blobs/{sha}.bin` (ảnh, dedupe). **Auto-trim** khi tổng blobs vượt `CACHE_MAX_BYTES` (mặc định 500MB) — xóa blob cũ nhất theo mtime. Thêm `cache/` vào `.gitignore`.
- **▶ trên node** = force chạy node đó + cache-hit upstream (vừa xem output vừa ép sinh ảnh mới). **▶ Chạy tổng** = cache-aware toàn bộ. **🗑 Xóa cache** = wipe.
- TDD: mỗi phase viết test trước. pytest CHƯA cài → test có block `__main__` runner, chạy: `backend\.venv\Scripts\python.exe test_xxx.py`.

## Dependencies

Độc lập — 2 plan trước (`260612-2328-codex-oauth`, `260613-1100-prompt-supplement`) đã `completed`, không xung đột. Engine memoization chèn vào `run_workflow` hiện có; giữ nguyên hành vi full-run + `test_e2e.py`/`test_nodes.py`.

## Constraints

- File code < 200 dòng → tách `engine_cache_key.py` khỏi `engine.py` nếu cần.
- KHÔNG phá: setup keepalive WS (`ws_ping_interval=None`), full-run, test_e2e/test_nodes.
- Backward-compat WS: `/ws/run` nhận cả envelope `{workflow,target,force}` lẫn workflow thuần.
- AI bất định: dùng lại ảnh cache là cố ý (tiết kiệm token); ▶ force để sinh mới.

## Validation Log

### Verification Results (Standard tier — 4 phases)
- Claims checked: 12 | Verified: 12 | Failed: 0 | Unverified: 0
- Verify trực tiếp (đã đọc file lúc viết plan): config ROOT_DIR/cache, engine.run_workflow/_topo_order, models.RunEvent/Workflow, providers PROVIDER_CLASSES/make_provider/resolve_model_config/provider_options, providers.base ImageProvider, nodes get_node_class/NODE_REGISTRY/resolve_params, api.openRunSocket, App PlayIcon/run/buildPayload, WorkflowNode header/useReactFlow, test_e2e (workflow thuần), test_nodes (__main__ runner).
- → Plan khớp codebase, đủ điều kiện triển khai.

### Interview (Session 1) — 4 câu
1. **▶ trên node AI** → **Force chạy tươi** node đó (tốn 1 token cho riêng nó), upstream cache-hit. ⇒ KHỚP plan (`force_ids={target}`). Không đổi.
2. **code_hash** → chỉ băm source CLASS node; sửa helper → 🗑 Xóa cache thủ công. ⇒ KHỚP plan. Không đổi.
3. **Dọn cache** → **Auto-trim khi vượt ngưỡng (mặc định 500MB → xóa blob cũ nhất theo mtime).** ⇒ **THAY ĐỔI** (plan cũ: không evict). Cập nhật Phase 1: thêm `CACHE_MAX_BYTES` + `_evict_if_needed()` trong `cache.save()`.
4. **Đổi model sau lưng config-name** → chấp nhận stale; key theo params (tên config). ⇒ KHỚP plan. Không đổi.

### Whole-Plan Consistency Sweep
- Quét lại plan.md + 4 phase sau khi propagate Q3.
- Phase 1: cache.py thêm eviction (architecture/steps/success/risk + test `test_evict`); risk "auto-evict để sau (YAGNI)" → đã thay bằng "đã implement (LRU theo mtime)". config.py thêm `CACHE_MAX_BYTES`.
- Không còn mâu thuẫn: Phase 2/3/4 không tham chiếu eviction → không bị ảnh hưởng. ▶ force, code_hash, model-stale nhất quán toàn plan.
- **0 mâu thuẫn chưa giải quyết** → đủ điều kiện cook.
