---
phase: 1
title: "Backend: lưu-trùng 409 + lưu trữ & API lịch sử exec"
status: pending
priority: P1
effort: "4h"
dependencies: []
status: completed
---

# Phase 1: Backend — save-conflict 409 + execution history

## Overview
Backend hiện silent overwrite khi lưu workflow trùng tên và **không lưu gì** về lần chạy.
Phase này: (a) thêm guard 409 khi tên trùng (opt-in ghi đè), (b) thêm bảng + API lưu **lịch sử exec** (metadata + tham chiếu ảnh cuối).

## Requirements
- Functional:
  - `POST /api/workflows` trả **409** nếu tên đã tồn tại và `overwrite` không bật; bật `overwrite=true` → lưu đè như cũ.
  - **Chỉ ghi exec cho ▶ Chạy (full) và ▶ Harness** — KHÔNG ghi ▶ chạy 1 node lẻ (target≠null & không harness) để lịch sử sạch (quyết định validation). `mode` ∈ {full, harness}.
  - Bản ghi exec: `workflow_name`, `mode`, `status` (running→success|error|stopped), `started_at`, `finished_at`, `duration_ms`, `error`, `harness` (điểm từng vòng + best), `nodes` (trạng thái từng node), `output_refs` (sha ảnh kết quả).
  - **Retention cap**: mỗi workflow giữ **50 bản ghi gần nhất** — `finish_execution` tự xóa bản ghi cũ hơn top-50 cùng `workflow_name` (quyết định validation).
  - API liệt kê + chi tiết + xóa exec, có paging.
- Non-functional: ảnh KHÔNG copy — chỉ lưu sha trỏ vào cache blob hiện có; bản ghi exec là JSON gọn (< vài KB/run).
<!-- Updated: Validation Session 1 - chỉ ghi full+harness, cap 50 bản ghi/workflow -->

> **[Validation verified]** Cấu trúc `outputs` trong event `node_finished` đã xác minh tại `engine.py:58-73`: mỗi handle là dict `{dtype:'image', size, sha}` (ảnh) hoặc `{dtype:'text', value}` (text). `harness_report.report` = `{best_iteration, best_score, history:[{iteration,score,passed}], stopped_early?}` (`engine.py:460-462`); `harness_iteration` mang `iteration/score/passed/message`. → Việc nhặt sha + điểm harness là chắc chắn, không phải đoán.

## Architecture
- **DB** (`backend/app/db.py`): bảng mới
  ```sql
  CREATE TABLE IF NOT EXISTS workflow_executions (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      workflow_name TEXT NOT NULL,
      mode         TEXT NOT NULL DEFAULT 'full',
      status       TEXT NOT NULL,            -- running|success|error|stopped
      error        TEXT NOT NULL DEFAULT '',
      detail       TEXT NOT NULL DEFAULT '{}', -- JSON: {nodes, harness, output_refs}
      started_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
      finished_at  TEXT,
      duration_ms  INTEGER
  );
  CREATE INDEX IF NOT EXISTS idx_exec_wf ON workflow_executions(workflow_name, id DESC);
  ```
  Hàm: `create_execution(name, mode) -> id`, `finish_execution(id, status, error, detail, duration_ms)`, `list_executions(name, limit, offset) -> (rows, total)`, `get_execution(id)`, `delete_execution(id) -> bool`, `clear_executions(name) -> int`. `save_workflow` giữ nguyên (đã ON CONFLICT); thêm `workflow_exists(name) -> bool`.
- **save guard** (`backend/app/main.py`): thêm field `overwrite: bool = False` vào model lưu (tạo `WorkflowSaveIn` bọc `Workflow` hoặc thêm query/body flag). Nếu `db.workflow_exists(name)` và không `overwrite` → `JSONResponse({"error":"exists","name":name}, status_code=409)`.
- **Ghi exec trong `ws_run`** (`backend/app/main.py`): suy `mode` = `harness` nếu `harness.enabled`, `full` nếu `target is None`, **ngược lại KHÔNG ghi** (chạy 1 node lẻ). Khi có ghi: `exec_id = db.create_execution(name, mode)`. Bọc `emit` để **gom**: trên `node_finished` lưu `nodes[node_id]=status` + nhặt `sha` từ `ev.outputs[handle]['sha']` khi `['dtype']=='image'` (cấu trúc đã xác minh `engine.py:58-73`); trên `harness_iteration`/`harness_report` lưu điểm/best. Khi `run_finished`/`run_error`/disconnect → `db.finish_execution(...)` với status + duration (`time.monotonic()`). Dùng `try/finally` để chạy bị ngắt vẫn chốt bản ghi (`stopped`). `finish_execution` cũng prune bản ghi cũ hơn top-50/workflow.
- **API mới** (`backend/app/main.py`):
  - `GET /api/workflows/{name}/executions?page=1&size=10` → `{items, total, page, size}`.
  - `GET /api/executions/{id}` → bản ghi đầy đủ (gồm `detail` đã parse).
  - `DELETE /api/executions/{id}` → `{deleted}`.
  - `DELETE /api/workflows/{name}/executions` → `{cleared: n}`.

## Related Code Files
- Modify: `backend/app/db.py` (bảng + hàm exec, `workflow_exists`)
- Modify: `backend/app/main.py` (save 409, ghi exec trong ws_run, 4 route exec)
- Read context: `backend/app/engine.py` (cách emit event để biết khóa `outputs`/sha), `backend/app/models.py`

## Implementation Steps
1. `db.py`: thêm `CREATE TABLE workflow_executions` + index vào `init_db()`; thêm các hàm exec + `workflow_exists`.
2. `main.py`: đổi handler `save_workflow` nhận `overwrite`; trả 409 khi trùng & chưa bật.
3. `main.py`: trong `ws_run`, suy `mode`, `create_execution`, bọc `emit` gom `nodes`/`harness`/`output_refs`, `finish_execution` trong `finally` (success/error/stopped + duration).
4. `main.py`: thêm 4 route exec (list paginated, detail, delete, clear).
5. Chạy backend, smoke test bằng `curl`/script: lưu trùng → 409; chạy 1 workflow → có bản ghi; list/detail/delete OK.

## Success Criteria
- [ ] Lưu workflow tên mới → 200; lưu lại trùng tên không `overwrite` → 409 `{"error":"exists"}`; có `overwrite=true` → 200 ghi đè.
- [ ] Chạy workflow (full + harness) → tạo bản ghi exec đúng status/duration; harness lưu điểm từng vòng + best.
- [ ] `GET .../executions?page=2&size=10` phân trang đúng `total`.
- [ ] `output_refs` chứa sha hợp lệ mở được qua `/api/cache-image/{sha}`.
- [ ] Backend compile/chạy không lỗi; bản ghi vẫn chốt khi client ngắt giữa chừng.

## Risk Assessment
- ~~Khóa output/sha~~: **Đã xác minh** `engine.py:58-73` — `outputs[handle]={dtype,size,sha}` cho ảnh. Không còn rủi ro đoán cấu trúc.
- **WAL + ghi exec khi WS ngắt**: dùng `finally` + kết nối riêng mỗi thao tác (đã theo pattern `_connect()`), tránh giữ transaction xuyên suốt run dài.
- **Phình DB**: đã chốt cap **50 bản ghi/workflow** (prune trong `finish_execution`) + route clear → không còn để mở.

## Security Considerations
- `name`/`sha` đi vào query phải tham số hóa (đã dùng `?` placeholder) — không nối chuỗi.
- `sha` chỉ render qua endpoint cache đã regex-validate sẵn.

## Next Steps
- Phase 2 dùng 409 cho confirm ghi đè + gọi API list executions.
