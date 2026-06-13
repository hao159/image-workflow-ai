---
phase: 2
title: "WS protocol target/force"
status: completed
priority: P1
effort: "0.25d"
dependencies: [1]
---

# Phase 2: WS protocol target/force

## Overview

Mở `/ws/run` để nhận `target` + `force` (chạy 1 node / chạy tới node), thêm `RunEvent.cached` cho UI biết node nào dùng cache, thêm `POST /api/cache/clear`. Giữ backward-compat: vẫn nhận workflow thuần (full run).

## Requirements

- Functional:
  - `/ws/run` nhận message JSON: envelope `{"workflow": {...}, "target": "id"|null, "force": ["id",...]}` HOẶC workflow thuần `{"name","nodes","edges"}` (full run, target=None, force=[]).
  - `run_workflow` được gọi với `target`/`force_ids` từ message.
  - `RunEvent` thêm `cached: bool = False`; emit kèm khi node_finished.
  - `POST /api/cache/clear` → `cache.clear()` → `{"cleared": true}`.
- Non-functional: giữ try/except + keepalive WS hiện tại; `main.py` gọn (tách parse nếu cần).

## Architecture

`models.py`:
```python
class RunEvent(BaseModel):
    ...
    cached: bool = False           # node_finished dùng output cache (không thực thi)

class RunRequest(BaseModel):
    workflow: Workflow
    target: Optional[str] = None
    force: list[str] = Field(default_factory=list)
```

`main.py ws_run`:
```python
raw = await ws.receive_text()
data = json.loads(raw)
if "workflow" in data:                      # envelope
    req = RunRequest.model_validate(data)
    wf, target, force = req.workflow, req.target, set(req.force)
else:                                        # workflow thuần (backward-compat)
    wf, target, force = Workflow.model_validate(data), None, set()
await run_workflow(wf, emit, target=target, force_ids=force)
```
(giữ ValidationError → run_error như cũ; bọc json.loads lỗi → run_error.)

`POST /api/cache/clear` → import `cache`, `cache.clear()`.

## Related Code Files

- Modify: `backend/app/models.py` (RunEvent.cached, RunRequest)
- Modify: `backend/app/main.py` (parse envelope/thuần, cache/clear endpoint)
- Modify: `backend/app/engine.py` (emit `cached=True/False` ở node_finished — nếu Phase 1 chưa gắn)
- Create: `backend/test_ws_cache.py` (cần backend chạy, node local — không token)
- Read for context: `backend/test_e2e.py` (giữ chạy được nguyên trạng)

## Implementation Steps

1. **Test trước** `test_ws_cache.py` (mẫu theo `test_e2e.py`, cần backend đang chạy):
   - Upload 1 ảnh; workflow local `load_image→filter(grayscale)→resize` (KHÔNG node AI → không token).
   - Run lần 1 (envelope, target=null) → tất cả `cached=false`.
   - Run lần 2 y hệt → các node `cached=true`.
   - Run `target` = node resize, `force=[resize]` → chỉ load_image/filter cache-hit, resize chạy lại (cached=false); KHÔNG có event cho node sau resize (ở đây resize là cuối nên kiểm prune bằng workflow có node save sau resize: target=resize ⇒ save không xuất hiện).
   - `POST /api/cache/clear` → run lại → tất cả cached=false.
   - Gửi workflow thuần (như test_e2e) → vẫn chạy (backward-compat).
2. `models.py`: thêm `cached` + `RunRequest`.
3. `main.py`: sửa `ws_run` parse 2 dạng; thêm endpoint `/api/cache/clear`.
4. Engine emit `cached` (nếu chưa).
5. Chạy backend (`backend\.venv\Scripts\python backend\run_server.py`) → chạy `test_ws_cache.py` + `test_e2e.py` → pass.

## Success Criteria

- [x] `test_ws_cache.py` pass: run2 cached=true, target prune đúng, clear reset, workflow thuần vẫn chạy.
- [x] `test_e2e.py` vẫn pass (không phá full-run).
- [x] `POST /api/cache/clear` trả `{"cleared": true}` và xóa cache thật.
- [x] WS không vỡ với cả 2 dạng message; lỗi parse → `run_error` rõ ràng.

## Risk Assessment

- **Message JSON hỏng** → bọc `json.loads` trong try, emit run_error thay vì crash WS.
- **Backward-compat**: phân biệt bằng key `"workflow"`; workflow thuần không có key này. An toàn vì Workflow luôn có `nodes`/`edges` ở top-level.
- **Test cần backend chạy** → ghi rõ trong docstring (giống test_e2e); không đưa vào unit chạy CI offline.
