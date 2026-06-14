---
phase: 3
title: "Frontend: bảng lịch sử exec kiểu n8n"
status: pending
priority: P2
effort: "5h"
dependencies: [1, 2]
status: completed
---

# Phase 3: Frontend — execution history panel (n8n-like)

## Overview
Trong modal "Mở workflow" (Phase 2), chọn 1 workflow → hiện **lịch sử thực thi** của nó: danh sách lần chạy (trạng thái, thời gian, thời lượng, điểm harness), có paging; bấm 1 lần chạy → **chi tiết** (ảnh sản phẩm cuối, trạng thái từng node, lỗi, các vòng harness).

## Requirements
- Functional:
  - Modal có 2 chế độ/tab: **Danh sách workflow** | **Lịch sử** (của workflow đang chọn).
  - Lịch sử: mỗi dòng = 1 exec với **badge trạng thái** (✓ success / ✗ error / ⏹ stopped), thời điểm bắt đầu, thời lượng (vd "12.3s"), `mode` (full/harness — chỉ 2 loại này được ghi), điểm best harness nếu có. **Paging** server-side (API `?page&size`).
  - Click 1 dòng → panel chi tiết: ảnh kết quả cuối (qua `/api/cache-image/{sha}`, click mở ImageViewer sẵn có), bảng trạng thái node, thông báo lỗi, danh sách vòng harness (điểm + feedback).
  - Nút **Xóa** 1 exec + **Xóa hết lịch sử** workflow (confirm).
- Non-functional: lazy — chỉ fetch executions khi mở tab Lịch sử cho workflow đó.

## Architecture
- **Component** `frontend/src/components/execution-history-panel.jsx` (~160 dòng): props `{ workflowName }`. State: `page`, `items`, `total`, `selected` (exec detail). Fetch qua `listExecutions`/`getExecution`. Render list + detail (master-detail trong panel).
- Tái dùng `ImageViewerContext` (đã có provider bao App) để ảnh history click-to-zoom — import `useImageViewer` nếu API cho phép; nếu không, render `<img>` + link tải.
- **workflow-browser-modal.jsx**: thêm tab switch; khi chọn workflow ở tab Danh sách → lưu `selectedName` → tab Lịch sử render `<ExecutionHistoryPanel workflowName={selectedName} />`.
- **CSS**: bổ sung vào `workflow-browser-modal.css` — badge trạng thái, layout master-detail, ảnh thumbnail.

## Related Code Files
- Create: `frontend/src/components/execution-history-panel.jsx`
- Modify: `frontend/src/components/workflow-browser-modal.jsx` (tab + selectedName), `frontend/src/styles/workflow-browser-modal.css`
- Read context: `frontend/src/ImageViewerContext.jsx` (cách mở viewer), `frontend/src/api.js` (4 hàm exec từ Phase 2)

## Implementation Steps
1. Đọc `ImageViewerContext.jsx` xác định cách trigger viewer từ component con.
2. Tạo `execution-history-panel.jsx`: fetch list (paging), render dòng + badge; click → `getExecution(id)` → detail.
3. Detail: map `detail.nodes` (bảng node→status), `detail.harness` (vòng+điểm+feedback), `detail.output_refs` (ảnh qua cache endpoint). Lỗi hiện `error`.
4. Thêm Xóa exec / Xóa hết (confirm) → refetch.
5. Ghép vào modal: tab "Danh sách | Lịch sử" + truyền `selectedName`.
6. Build + chạy thật: chạy vài workflow (full + harness) → xem lịch sử + chi tiết + ảnh.

## Success Criteria
- [ ] Chọn workflow → tab Lịch sử liệt kê đúng các lần chạy, mới nhất trước, có paging.
- [ ] Badge trạng thái + thời lượng + mode hiển thị đúng.
- [ ] Click exec → chi tiết: ảnh cuối mở được full-res, trạng thái node + vòng harness + lỗi đúng.
- [ ] Xóa 1 exec / xóa hết hoạt động, danh sách cập nhật.
- [ ] Không fetch executions khi chưa mở tab Lịch sử (lazy).

## Risk Assessment
- **Ảnh sha đã bị dọn khỏi cache** (cache LRU theo `CACHE_MAX_BYTES`): endpoint trả 404 → hiện placeholder "ảnh đã bị dọn" thay vì vỡ layout.
<!-- Updated: Validation Session 1 - chỉ ghi full+harness nên không còn nhiễu mode=node -->
- ~~Nhiễu mode=node~~: đã loại — Phase 1 không ghi exec cho chạy 1 node lẻ.

## Security Considerations
- Không render HTML thô từ `error`/`feedback` (React escape mặc định) — giữ nguyên text.

## Next Steps
- Phase 5 QA tổng + docs cho tính năng history.
