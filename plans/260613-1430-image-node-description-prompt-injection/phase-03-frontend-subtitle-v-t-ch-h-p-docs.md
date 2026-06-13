---
phase: 3
title: "Frontend subtitle và tích hợp docs"
status: completed
priority: P2
effort: "2h"
dependencies: [1, 2]
---

# Phase 3: Frontend subtitle + tích hợp + docs

## Overview

Hiện mô tả ảnh làm **phụ đề trên header node** (vai trò "đặt tên node"), verify thật trên AI đa-ảnh (Gemini), và cập nhật docs/README/memory. Ô nhập "Mô tả ảnh" đã TỰ hiện (param `text` render qua `NodeParamField` default case ở Phase 1) → frontend chỉ cần thêm phụ đề.

## Requirements

- Functional:
  - Node có param `is_image_label` và giá trị khác rỗng → hiện phụ đề dưới tiêu đề (vd header: `Tải ảnh lên` + dòng nhỏ `cái áo sơ mi trắng`).
  - Trống mô tả → không hiện phụ đề (header như cũ).
- Non-functional: chỉ sửa `WorkflowNode.jsx` + 1 ít CSS; không đụng luồng dữ liệu.

## Architecture

`WorkflowNode.jsx`: từ `meta.params` tìm spec có `is_image_label` → lấy `params[spec.name]`; nếu có giá trị, render `<div className="wf-node-subtitle">{value}</div>` ngay dưới `.wf-node-title` (hoặc dưới `.wf-node-header`). Thêm style nhỏ (font nhỏ, màu mờ, ellipsis 1 dòng) vào CSS node hiện có.

```jsx
const labelSpec = meta.params.find((p) => p.is_image_label)
const nodeLabel = labelSpec ? (params[labelSpec.name] || '').trim() : ''
// ... trong header, sau wf-node-title hoặc ngay dưới header:
{nodeLabel && <div className="wf-node-subtitle nodrag" title={nodeLabel}>{nodeLabel}</div>}
```

## Related Code Files

- Modify: `frontend/src/components/WorkflowNode.jsx` (phụ đề), CSS node tương ứng (tìm file style đang dùng cho `.wf-node-header`)
- Modify (docs): `README.md` (bảng node + ví dụ workflow đa-ảnh), `docs/*` nếu có mục node, `MEMORY.md` + memory file dự án
- Test thật: workflow Gemini 2 ảnh

## Implementation Steps

1. `WorkflowNode.jsx`: thêm `labelSpec`/`nodeLabel`, render phụ đề (chỉ khi có giá trị). Thêm CSS `.wf-node-subtitle`.
2. Build/lint frontend: `npm run build --prefix frontend` (hoặc `npm run lint`) → không lỗi.
3. **Verify thật (quan trọng — rủi ro chính):** chạy backend + frontend; dựng workflow 2× `Tải ảnh lên` (mô tả "cái áo" / "người mẫu") → `Sửa ảnh` (config **Gemini**) prompt "mặc áo ở Ảnh 1 lên người ở Ảnh 2" → chạy, xác nhận ảnh ghép ĐÚNG đối tượng. Bật `CODEX_DEBUG`/log để xác nhận prompt gửi đi chứa khối tham chiếu. Nếu Gemini lệch → thử lặp số trong câu, hoặc đổi header khối sang tiếng Anh.
4. Cập nhật docs:
   - `README.md`: mục "Các node có sẵn" ghi node ảnh có ô "Mô tả ảnh"; thêm ví dụ workflow đa-ảnh dùng `Ảnh 1/Ảnh 2`.
   - Memory dự án (`image-workflow-project.md`) + `MEMORY.md`: ghi cơ chế nhãn-đi-theo-ảnh + cache (mô tả không vào node_key, nối out_key).
5. (Tùy chọn) `docs-manager` cập nhật `docs/system-architecture.md` nếu có mô tả engine.

## Success Criteria

- [ ] Node nguồn có mô tả → hiện phụ đề; trống → không hiện.
- [ ] Frontend build/lint sạch.
- [ ] **Verify thật Gemini:** workflow 2 ảnh ghép đúng đối tượng theo Ảnh 1/Ảnh 2; prompt gửi đi chứa khối tham chiếu (xác nhận qua log).
- [ ] README + memory cập nhật.

## Risk Assessment

- **AI (Gemini/gpt-image/codex) không tôn trọng "Ảnh 1/2".** Đây là rủi ro lõi của cả tính năng. Mitigation: verify thật trên Gemini (mạnh nhất); nếu yếu, tinh chỉnh wording khối tham chiếu (lặp số, tiếng Anh) — chỉ sửa `image_label_block.py`, không đụng kiến trúc. Ghi rõ provider nào best-effort trong README.
- **Phụ đề làm vỡ layout node** nếu mô tả dài. Mitigation: ellipsis 1 dòng + `title` tooltip đầy đủ.
- Frontend chưa có test tự động → bước verify là thủ công; ghi lại kết quả vào memory.

## Next Steps

- Sau khi verify: cân nhắc (ngoài scope) badge số `Ảnh N` ngay tại cổng vào node `Sửa ảnh` để người dùng biết thứ tự mà không cần đoán theo cạnh nối.
