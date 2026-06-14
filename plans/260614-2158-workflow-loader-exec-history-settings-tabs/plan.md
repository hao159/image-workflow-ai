---
title: 'Workflow loader modal + lịch sử exec (n8n) + cảnh báo lưu trùng + tab Cài đặt'
description: >-
  Đổi dropdown Workflows thành nút mở modal danh sách giữa màn hình có paging;
  cảnh báo ghi đè khi lưu trùng tên; thêm lịch sử thực thi từng workflow kiểu n8n
  (metadata + ảnh cuối); chia Cài đặt thành tab theo loại (Giao diện | Model).
status: completed
priority: P2
branch: feat/neutral-theme-redesign
tags:
  - frontend
  - backend
  - workflow
  - settings
  - history
blockedBy: []
blocks: []
created: '2026-06-14T21:58:00.000Z'
createdBy: 'ck:plan'
source: skill
---

# Workflow loader modal + lịch sử exec + cảnh báo lưu trùng + tab Cài đặt

## Overview

4 thay đổi UX/tính năng quanh quản lý workflow + cài đặt:

1. **Nút "Mở workflow"** → modal giữa màn hình liệt kê workflow đã lưu, **có paging** (thay dropdown `showWorkflows` trong toolbar).
2. **Lưu trùng tên** → backend trả 409, frontend **hỏi xác nhận ghi đè** (hiện đang silent overwrite).
3. **Lịch sử exec từng workflow** (kiểu n8n) — lưu **metadata + tham chiếu ảnh cuối** (tái dùng cache blob): thời gian, trạng thái, thời lượng, lỗi, điểm harness từng vòng, trạng thái từng node. Xem lại được ảnh sản phẩm.
4. **Tab Cài đặt theo loại** — chia modal Cài đặt 1-trang-dài thành tab **Giao diện | Model** (OAuth nằm trong tab Model theo provider codex).

## Quyết định người dùng (locked)

- **History depth:** Metadata + ảnh cuối (sha ref vào cache blob, không nhân đôi dữ liệu).
- **Lưu trùng:** Hỏi xác nhận ghi đè (backend 409 + confirm frontend).
- **Tab Cài đặt:** Giao diện | Model (OAuth trong tab Model).
- **Ghi exec:** Chỉ ▶ Chạy (full) + ▶ Harness; KHÔNG ghi ▶ chạy 1 node lẻ. *(validation)*
- **Retention:** Giữ 50 bản ghi gần nhất/workflow, tự prune trong `finish_execution`. *(validation)*
- **Tab mặc định:** Modal Cài đặt mở ở tab Model. *(validation)*

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Backend: lưu-trùng 409 + lưu trữ & API lịch sử exec](./phase-01-backend-save-conflict-and-execution-history.md) | Done |
| 2 | [Frontend: modal Mở workflow (paging) + confirm ghi đè](./phase-02-frontend-workflow-loader-modal-and-overwrite-confirm.md) | Done |
| 3 | [Frontend: bảng lịch sử exec kiểu n8n](./phase-03-frontend-execution-history-panel.md) | Done |
| 4 | [Frontend: tab hóa modal Cài đặt (Giao diện \| Model)](./phase-04-frontend-settings-modal-tabs.md) | Done |
| 5 | [QA, test & tài liệu](./phase-05-qa-tests-docs.md) | Done |

## Thứ tự thực thi

Tuần tự: 1 → 2 → 3 → 4 → 5.
- Phase 1 đặt nền backend (API exec history + 409) — Phase 2/3 phụ thuộc.
- Phase 2 dựng modal loader + sửa luồng lưu; Phase 3 cắm panel history vào modal đó.
- Phase 4 độc lập (chỉ chạm SettingsModal) — có thể làm song song với 2/3 nếu muốn.
- Phase 5 chốt test + docs.

## Dependencies

- Plan `260614-2109-neutral-redesign-system-theme` đã **completed** → token theme + style toolbar/modal đã sẵn; tái dùng class/var hiện có (`.modal`, `.wf-menu`, status chip).
- Tái dùng `/api/cache-image/{sha}` cho ảnh history (không tạo storage mới cho ảnh).
- Không phụ thuộc plan đang mở khác.

## Validation Log

### Session 1 (2026-06-14)

**Verification (Full tier, 5 phases):**
- Claims checked: 9 | Verified: 7 | Failed: 1 (đã sửa) | Unverified: 0
- ✅ `node_finished.outputs` = `{handle:{dtype,size,sha}}` — `engine.py:58-73`.
- ✅ `harness_report.report` = `{best_iteration,best_score,history}`; `harness_iteration`={iteration,score,passed,message} — `engine.py:446-462`.
- ✅ `save_workflow` hiện `ON CONFLICT DO UPDATE` (silent overwrite) — `db.py:124-130`; dropdown `showWorkflows` — `App.jsx:558-579`.
- ✅ `SettingsModal.jsx` 255 dòng (>200, cần tách); `settings-modal.css`, `toolbar.css`, `ImageViewerContext.jsx` tồn tại.
- ❌→✅ **Failed (đã sửa):** Test KHÔNG ở `backend/tests/` (không tồn tại) → phẳng trong `backend/` theo `test_ws_cache.py`. `pytest.exe` đã có trong venv (note bộ nhớ cũ sai). Phase 5 đã cập nhật path + thêm pytest vào requirements.

**Câu hỏi đã chốt (3):**
1. Ghi exec → **full + harness** (bỏ node lẻ). → Phase 1, 3.
2. Retention → **giữ 50/workflow, tự prune**. → Phase 1, 5.
3. Tab mặc định → **Model**. → Phase 4.

**Whole-Plan Consistency Sweep:** Re-đọc plan.md + 5 phase. `mode` thống nhất {full,harness} (Phase 1 ↔ Phase 3); cap 50 nhất quán (Phase 1 làm, Phase 5 test, không quyết định lại); test path phẳng `backend/` nhất quán (Phase 5). **0 mâu thuẫn tồn đọng.**

### Hoàn thành (2026-06-14)

Toàn bộ 5 phase **Done**. Tóm tắt triển khai:
- **BE** (`db.py`, `main.py`): bảng `workflow_executions` + 6 hàm exec + `workflow_exists`; save 409 (`?overwrite`); `ws_run` ghi exec full+harness (try/finally chốt khi ngắt → `stopped`), prune 50; 4 route exec.
- **FE**: `workflow-browser-modal.jsx` (paging + 2 tab), `execution-history-panel.jsx` (master-detail + ảnh qua cache), `App.jsx` `doSave(overwrite)` + confirm 409; `SettingsModal` tách 3 file (shell + 2 tab, mặc định Model).
- **Test**: `test_workflow_save_conflict.py` + `test_execution_history.py` — **6/6 pass**; regression **103/103 pass**; `test_engine_cache` vẫn fail 8/9 (pre-existing, không phải regression); frontend build pass. `pytest` đã thêm vào `requirements.txt`.
- **Docs**: README thêm mục "Mở workflow & lịch sử chạy" + ghi chú lưu-trùng/tab Cài đặt. (`docs/` chỉ có `journals/` — không có codebase-summary/system-architecture để sync.)
- **Code review**: 0 Critical/High/Medium; chỉ ghi chú cosmetic (emoji 🕘, silent catch detail) — giữ theo YAGNI.

**Câu hỏi tồn đọng:** Không.
