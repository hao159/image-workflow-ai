---
phase: 5
title: "QA, test & tài liệu"
status: pending
priority: P3
effort: "3h"
dependencies: [1, 2, 3, 4]
status: completed
---

# Phase 5: QA, test & tài liệu

## Overview
Chốt chất lượng: test backend cho save-409 + API exec history, QA tay luồng frontend, cập nhật README + docs. Quyết định cap số bản ghi history (giữ/không) dựa trên thực tế dùng.

## Requirements
- Functional: test tự động cho hành vi backend mới; QA tay 4 tính năng; docs cập nhật.
- Non-functional: không làm hỏng test cũ (lưu ý `test_engine_cache.py` đã fail sẵn 8/9 — pre-existing, KHÔNG tính là regression của plan này).
<!-- Updated: Validation Session 1 - sửa vị trí test: flat backend/, theo test_ws_cache.py; pytest đã có trong venv -->

> **[Validation verified]** Test KHÔNG nằm trong `backend/tests/` (thư mục đó không tồn tại) — chúng **phẳng trong `backend/`** (vd `test_ws_cache.py`, `test_harness_loop.py`, `test_nodes.py`). `pytest.exe` **đã có** trong `backend/.venv/Scripts/` (note bộ nhớ "pytest missing" đã cũ/sai). Tham chiếu style: `backend/test_ws_cache.py` (test tầng WS — gần nhất với việc ghi exec qua `/ws/run`).

## Architecture
- **Test backend** (phẳng trong `backend/`, theo style `test_ws_cache.py`):
  - `backend/test_workflow_save_conflict.py`: lưu mới → 200; lưu trùng không overwrite → 409; overwrite=true → 200.
  - `backend/test_execution_history.py`: tạo exec → finish → list (paging) → detail → delete → clear; kiểm `duration_ms`/`status`/`detail` đúng + **prune giữ đúng 50** (tạo 55 bản ghi → còn 50).
- **pytest**: đã có trong venv; **bổ sung `pytest` vào `backend/requirements.txt`** cho tái lập môi trường (hiện thiếu).
- **QA tay** (checklist dưới Success Criteria).
- **Docs**: README mục mới "Mở workflow & lịch sử chạy"; cân nhắc thêm vào `docs/codebase-summary.md`/`system-architecture.md` (bảng `workflow_executions` + route mới) nếu các file đó tồn tại & đang được maintain.
- **Cap history**: đã chốt **giữ 50 gần nhất/workflow** (làm ở Phase 1) → Phase 5 chỉ **test** prune, không quyết định lại.

## Related Code Files
- Create: `backend/test_workflow_save_conflict.py`, `backend/test_execution_history.py`
- Modify: `README.md`, `backend/requirements.txt` (thêm pytest); (tùy) `docs/codebase-summary.md`, `docs/system-architecture.md`
- Read context: `backend/test_ws_cache.py` để khớp fixture/style (khởi tạo app/DB tạm)

## Implementation Steps
1. Đọc `backend/test_ws_cache.py` để khớp cách khởi tạo app/DB tạm (override `config.DB_PATH`).
2. Viết 2 file test phẳng trong `backend/`; chạy `backend\.venv\Scripts\python.exe -m pytest backend/test_workflow_save_conflict.py backend/test_execution_history.py -q`.
3. Sửa tới khi pass (KHÔNG dùng mock giả để qua bài).
4. Thêm `pytest` vào `backend/requirements.txt`.
5. QA tay theo checklist; ghi kết quả.
6. Cập nhật README (+ docs nếu maintain).
7. `npm run build --prefix frontend` lần cuối.

## Todo List
- [ ] test_workflow_save_conflict pass
- [ ] test_execution_history pass
- [ ] test prune giữ đúng 50 bản ghi/workflow
- [ ] QA tay xong
- [ ] README cập nhật + pytest vào requirements.txt

## Success Criteria (gồm QA tay)
- [ ] 2 file test mới pass; test cũ không bị plan này làm fail thêm.
- [ ] QA: nút "Mở workflow" → modal paging; Tải/Xóa OK.
- [ ] QA: lưu trùng → confirm ghi đè; tên mới → lưu thẳng.
- [ ] QA: lịch sử exec liệt kê + chi tiết (ảnh/node/harness/lỗi) đúng; paging OK; xóa OK.
- [ ] QA: Cài đặt 2 tab hoạt động, không regression.
- [ ] README phản ánh tính năng mới.

## Risk Assessment
- **Test DB lẫn DB thật**: dùng DB tạm/đường dẫn override trong test (kiểm `config.DB_PATH` có override được không; nếu không, thêm hook nhỏ). Mitigation: đọc test cũ trước.
- **Pre-existing engine cache test fail**: ghi rõ trong báo cáo để không nhầm là regression.

## Security Considerations
- Không commit DB/khóa; test dùng dữ liệu giả an toàn.

## Next Steps
- `/ck:journal` ghi nhật ký; cân nhắc tách nhánh riêng nếu chưa muốn trộn với nhánh redesign.
