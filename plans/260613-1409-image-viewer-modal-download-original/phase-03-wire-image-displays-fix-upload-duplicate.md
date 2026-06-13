---
phase: 3
title: Wire image displays + fix upload duplicate
status: completed
priority: P1
effort: 1.5h
dependencies:
  - 1
  - 2
---

# Phase 3: Wire image displays + fix upload duplicate

## Overview
Nối mọi điểm hiển thị ảnh vào modal (Phase 2) + dựng URL ảnh gốc đúng theo loại node (Phase 1 cho node AI/Biến đổi). Bỏ ảnh trùng trên node Tải ảnh lên.

## Key Insights — 3 điểm hiển thị ảnh hiện tại
| Điểm | File:dòng | Hành vi cũ | URL ảnh gốc |
|---|---|---|---|
| Ô upload (param) | `NodeParamField.jsx:49,51` | `window.open(url)` | `/api/uploads/{file_id}` (đã full-res) |
| Preview kết quả | `WorkflowNode.jsx:143-147` | không click được | `/api/cache-image/{sha}` (từ `outputs[handle].sha`) |
| Card Lưu ảnh | `WorkflowNode.jsx:10-23` | `window.open(url)` | `/api/outputs/{name}` (đã full-res) |

## Vấn đề "2 ảnh" (đã verify)
Node `load_image` (`meta.type === 'load_image'`): ô upload (`ImageUploadField`) đã hiện ảnh; sau khi chạy backend trả `image` bytes → engine sinh `preview` → khối `wf-node-preview` (`WorkflowNode.jsx:143`) hiện ảnh thứ 2 trùng. Fix: bỏ render `wf-node-preview` khi `meta.type === 'load_image'` (ô upload là nguồn ảnh chính, click vào nó vẫn mở modal).

## Requirements
- Functional:
  - Click ảnh ở cả 3 điểm → mở modal (Phase 2) với src = URL ảnh gốc + filename hợp lý.
  - Node `load_image` chỉ hiện 1 ảnh (ô upload), không hiện preview trùng.
  - Node AI/Biến đổi: src modal = `/api/cache-image/{sha}` (full-res), KHÔNG dùng thumbnail preview làm src tải.
- Non-functional: giữ thumbnail nhẹ cho `<img>` inline (preview), chỉ full-res khi mở modal; không phá cache badge / status.

## Architecture
```
WorkflowNode:
  imageOutput = Object.values(outputs).find(o => o.dtype==='image')   // có .sha
  fullResUrl  = imageOutput ? `/api/cache-image/${imageOutput.sha}` : null
  preview <img> onClick → openViewer({src: fullResUrl ?? preview, filename: `${meta.title}.png`})
  ẩn preview nếu meta.type==='load_image'
FileResultCard: onClick thumb/btn → openViewer({src: url, filename})  (url=/api/outputs/..)
ImageUploadField: onClick → openViewer({src: url, filename: value})   (url=/api/uploads/..)
```

## Related Code Files
- Modify: `frontend/src/components/WorkflowNode.jsx`
  - `FileResultCard`: thay `window.open` bằng `openViewer` (click thumb + nút → mở modal); giữ/đổi nút thành "xem".
  - Thân `WorkflowNode`: tính `imageOutput`/`fullResUrl` từ `outputs`; preview `<img>` thêm `onClick` mở modal; **điều kiện ẩn preview cho `load_image`**.
  - `import { useImageViewer } from '../ImageViewerContext.jsx'`.
- Modify: `frontend/src/components/NodeParamField.jsx`
  - `ImageUploadField`: `img onClick` + nút "Xem ảnh gốc" → `openViewer({src:url, filename:value})` thay `window.open`.
- Read context: `frontend/src/components/ImageViewerModal.jsx`, `ImageViewerContext.jsx` (API `openViewer`), `engine.py` `_meta` (field `sha`).

## Implementation Steps
1. WorkflowNode: thêm `const { openViewer } = useImageViewer()`.
2. Tính image output gốc:
   ```js
   const imageOutput = outputs ? Object.values(outputs).find((o) => o.dtype === 'image') : null
   const fullResUrl = imageOutput?.sha ? `/api/cache-image/${imageOutput.sha}` : null
   ```
3. Khối preview: ẩn cho upload node + cho click mở modal:
   ```jsx
   {preview && meta.type !== 'load_image' && (
     <div className="wf-node-preview">
       <img src={preview} alt="kết quả"
            onClick={() => openViewer({ src: fullResUrl ?? preview, filename: `${meta.title}.png` })} />
     </div>
   )}
   ```
   (cursor: zoom-in cho ảnh preview trong css `wf-node-preview img`).
4. `FileResultCard({ url })`: nhận thêm prop hoặc gọi `useImageViewer` trong component; click thumb + nút → `openViewer({ src: url, filename: url.split('/').pop() })`. Bỏ `window.open`.
5. `ImageUploadField`: `img onClick` + nút mắt → `openViewer({ src: url, filename: value })`. Bỏ `window.open`.
6. CSS: `wf-node-preview img { cursor: zoom-in }` (`styles/workflow-node.css:270`).
7. Compile/build-check: `npm run build --prefix frontend` pass.

## Todo List
- [ ] WorkflowNode dùng `useImageViewer`, tính `fullResUrl` từ `outputs[].sha`
- [ ] Ẩn `wf-node-preview` khi `meta.type === 'load_image'`
- [ ] preview `<img>` click → modal (full-res nếu có sha)
- [ ] FileResultCard click → modal
- [ ] ImageUploadField click + nút "xem" → modal
- [ ] css `cursor: zoom-in` cho preview
- [ ] Build frontend pass

## Success Criteria
- [ ] Node Tải ảnh lên chỉ hiển thị **1 ảnh** (ô upload), không còn ảnh preview trùng.
- [ ] Click ảnh ở: Tải ảnh lên / Tạo ảnh AI / Sửa ảnh AI / Lưu ảnh / Biến đổi → mở modal xem ảnh.
- [ ] Modal node AI/Biến đổi hiển thị **ảnh gốc full-res** (qua `/api/cache-image/{sha}`), nút "Tải ảnh gốc" tải đúng PNG gốc (không phải thumbnail).
- [ ] Modal upload/lưu ảnh tải đúng file gốc.
- [ ] Không còn `window.open` cho ảnh (thay bằng modal); build pass.

## Risk Assessment
- **Node ảnh chưa chạy (chưa có `outputs.sha`)** → `fullResUrl=null`, modal fallback `preview` (thumbnail). Chấp nhận: chỉ là ảnh xem tạm trước khi có gốc; sau khi chạy có sha thì đủ gốc.
- **Workflow cũ load lại không có `outputs`** → preview rỗng, không có gì để click; không lỗi.
- **`meta.type` cho upload** = `load_image` (verify `inputs.py:21`); nếu sau đổi type_name phải sửa điều kiện — comment giải thích "ảnh đã hiện ở ô upload" (KHÔNG ref số phase/finding, theo rule code-comments).

## Security Considerations
- src modal luôn là URL nội bộ (`/api/...`); filename sanitize không cần (chỉ gợi ý tên tải).

## Next Steps
- Verify thủ công: chạy backend (`backend\.venv\Scripts\python backend\run_server.py --reload`) + frontend (`npm run dev --prefix frontend`), kéo node, chạy, click ảnh, tải gốc, so sánh kích thước file tải > thumbnail.
- Cân nhắc cập nhật `docs/` nếu có mô tả UI node (docs-manager).
