---
phase: 2
title: "Frontend: modal Mở workflow (paging) + confirm ghi đè"
status: pending
priority: P1
effort: "4h"
dependencies: [1]
status: completed
---

# Phase 2: Frontend — workflow loader modal + overwrite confirm

## Overview
Đổi dropdown `showWorkflows` trong toolbar thành **nút "Mở workflow"** mở **modal giữa màn hình** liệt kê workflow đã lưu, có **paging**. Sửa luồng Lưu để **hỏi xác nhận ghi đè** khi backend trả 409.

## Requirements
- Functional:
  - Toolbar có nút **📂 Mở workflow** (bỏ panel dropdown cũ). Bấm → modal giữa màn hình.
  - Modal: danh sách workflow (tên + ngày cập nhật), nút **Tải** + **Xóa** mỗi dòng, **phân trang** (client-side, ~8 dòng/trang) với prev/next + chỉ số trang.
  - Lưu workflow: nếu 409 → `confirm("Workflow \"X\" đã tồn tại. Ghi đè?")` → đồng ý gọi lại với `overwrite=true`; hủy → giữ nguyên, báo "Đã hủy lưu".
- Non-functional: tái dùng class `.modal`/`.modal-backdrop`/`.modal-header` sẵn có; đóng bằng ✕ / Esc / click nền.

## Architecture
- **Component mới** `frontend/src/components/workflow-browser-modal.jsx` (~150 dòng): props `{ onClose, onLoad(name), onDelete(name), workflows }` hoặc tự fetch qua `listWorkflows`. Quản state: `page`, danh sách. Paging client-side: `slice(page*size, ...)`. (Tab lịch sử exec thêm ở Phase 3 — để chỗ cắm sẵn: layout 2 cột / hoặc 2 tab "Danh sách | Lịch sử").
- **App.jsx**:
  - Bỏ block `wf-menu` + `showWorkflows` panel (dòng ~558-579); thêm nút mở modal + state `showWorkflowBrowser`.
  - `save`: bắt lỗi 409 → confirm → `saveWorkflow(payload, { overwrite:true })`. Refactor thành hàm `doSave(overwrite)`.
  - `load`/`removeWorkflow` giữ nguyên, truyền vào modal.
- **api.js**: `saveWorkflow(workflow, { overwrite = false } = {})` — gắn `overwrite` vào body; ném lỗi đặc biệt khi 409 (vd `err.code = 'exists'`) để App phân biệt. Thêm `listExecutions`, `getExecution`, `deleteExecution`, `clearExecutions` (dùng ở Phase 3, khai báo sẵn ở đây để gọn 1 lượt).
- **CSS** `frontend/src/styles/workflow-browser-modal.css` (import vào main hoặc styles.css): list rows, pager. Tái dùng token theme.

## Related Code Files
- Create: `frontend/src/components/workflow-browser-modal.jsx`, `frontend/src/styles/workflow-browser-modal.css`
- Modify: `frontend/src/App.jsx` (bỏ dropdown, thêm nút + modal + luồng save), `frontend/src/api.js` (overwrite + 4 hàm exec), `frontend/src/main.jsx` (import css nếu cần)

## Implementation Steps
1. `api.js`: cập nhật `saveWorkflow` nhận `overwrite`; phân biệt 409 (đọc body `{error:'exists'}` → ném `Error` có `.code='exists'`). Thêm `listExecutions(name,{page,size})`, `getExecution(id)`, `deleteExecution(id)`, `clearExecutions(name)`.
2. Tạo `workflow-browser-modal.jsx`: modal + danh sách + paging client-side + nút Tải/Xóa. Để sẵn cấu trúc tab/cột cho history (Phase 3).
3. Tạo css; import.
4. `App.jsx`: thay `wf-menu`(Workflows) bằng nút "Mở workflow" + render `<WorkflowBrowserModal>` khi `showWorkflowBrowser`. Bỏ state `showWorkflows`.
5. `App.jsx`: refactor `save` → `doSave(overwrite=false)`; bắt `.code==='exists'` → confirm → `doSave(true)`.
6. `npm run build --prefix frontend` (hoặc dev) kiểm tra không lỗi; thử lưu trùng → confirm; mở modal → paging chạy.

## Success Criteria
- [ ] Nút "Mở workflow" mở modal giữa màn hình; dropdown cũ đã bỏ.
- [ ] Danh sách phân trang đúng (prev/next, ẩn/disable ở biên); Tải/Xóa hoạt động.
- [ ] Lưu trùng tên → hiện confirm ghi đè; đồng ý → ghi đè OK; hủy → không đổi gì, status "Đã hủy lưu".
- [ ] Lưu tên mới → không hỏi, lưu thẳng.
- [ ] Đóng modal bằng ✕/Esc/nền; build frontend pass.

## Risk Assessment
- **Phá vỡ luồng load hiện tại**: `load()` đang đóng `showWorkflows`; chuyển sang đóng modal mới. Mitigation: giữ chữ ký `load(name)`, modal gọi `onLoad` rồi `onClose`.
- **savedList stale sau lưu/xóa**: tiếp tục `setSavedList(await listWorkflows())` sau mỗi thao tác.

## Security Considerations
- `name` encode khi vào URL (đã có `encodeURIComponent` trong api.js).

## Next Steps
- Phase 3 cắm panel lịch sử exec vào modal này (dùng 4 hàm api đã thêm).
