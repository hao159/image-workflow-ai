---
phase: 2
title: Image viewer modal + context
status: completed
priority: P2
effort: 2h
dependencies: []
---

# Phase 2: Image viewer modal + context

## Overview
Lightbox dùng chung: click ảnh ở bất kỳ node nào → overlay full-screen xem ảnh full-res + nút "Tải ảnh gốc" + đóng (X / click nền / Esc). Cung cấp qua React Context để component lồng sâu gọi được.

## Key Insights
- `ImageUploadField` lồng sâu (App→ReactFlow→WorkflowNode→NodeParamField→ImageUploadField); ReactFlow tự khởi tạo node nên KHÔNG prop-drill được → phải dùng Context (đúng mẫu `RunContext.jsx` đã có).
- `RunContext.Provider` đã wrap quanh ReactFlow trong App — đặt `ImageViewerProvider` cùng chỗ.
- Style theo token sẵn có (`var(--bg-...)`, `var(--radius-*)`, `var(--accent)`); mẫu modal đã có ở `styles/settings-modal.css` (tham khảo backdrop/z-index).
- Tải file: `<a href={url} download={filename}>` — tất cả URL cùng origin (proxy Vite `/api`) nên `download` đặt được tên. Không cần fetch→blob (KISS).

## Requirements
- Functional: `openViewer({src, filename})` mở modal hiển thị `<img src>` + nút tải (href=src, download=filename) + nút mở tab mới (tùy chọn, giữ hành vi cũ).
- Đóng bằng: nút X, click backdrop, phím Esc. Khóa scroll nền khi mở.
- Non-functional: 1 instance modal duy nhất; component < 200 dòng; a11y cơ bản (Esc, focus nút đóng, `role="dialog"`).

## Architecture
```
ImageViewerContext  { openViewer({src, filename}) }
ImageViewerProvider (state: current={src,filename}|null)
  ├─ render children
  └─ render <ImageViewerModal> khi current != null
WorkflowNode / ImageUploadField  ── useImageViewer().openViewer(...) ──▶ mở
```

## Related Code Files
- Create: `frontend/src/ImageViewerContext.jsx` — context + provider + hook `useImageViewer()` (giống `RunContext.jsx`).
- Create: `frontend/src/components/ImageViewerModal.jsx` — UI lightbox.
- Create: `frontend/src/styles/image-viewer-modal.css` — style overlay/ảnh/nút.
- Modify: `frontend/src/App.jsx` — bọc `ImageViewerProvider` (cạnh `RunContext.Provider`).
- Modify: `frontend/src/styles.css` (hoặc nơi import css) — `@import` css mới.
- Read context: `frontend/src/RunContext.jsx`, `frontend/src/components/SettingsModal.jsx`, `frontend/src/components/icons.jsx` (đã có `XIcon`, `ExternalLinkIcon`; cần thêm `DownloadIcon`).

## Implementation Steps
1. `icons.jsx`: thêm `DownloadIcon` (mũi tên xuống + khay) — style Lucide stroke 2.
2. `ImageViewerContext.jsx`: `createContext`, `ImageViewerProvider` giữ state `view` (`{src, filename}|null`), `openViewer(v)` set, `closeViewer()` null; render `children` + `<ImageViewerModal view onClose/>` khi mở; export `useImageViewer()`.
3. `ImageViewerModal.jsx`:
   - Overlay `.img-viewer-overlay` (onClick nền → đóng; `stopPropagation` trên khung ảnh).
   - `<img className="img-viewer-img" src={view.src}>`.
   - Thanh action: nút **Tải ảnh gốc** (`<a download={view.filename} href={view.src}>` + `DownloadIcon`), nút mở tab mới (`ExternalLinkIcon`), nút đóng (`XIcon`).
   - `useEffect`: listener `keydown` Esc → `onClose`; `document.body.style.overflow='hidden'` khi mở, khôi phục khi unmount.
4. `image-viewer-modal.css`: overlay `position:fixed; inset:0; z-index` cao hơn settings-modal; nền mờ; ảnh `max-width/height: ~90vw/85vh; object-fit:contain`; thanh action góc trên phải.
5. `App.jsx`: import provider + đặt bọc quanh phần render chính (cùng vị trí `RunContext.Provider`). Import css mới (theo cách App import các css khác).
6. Compile-check frontend: `npm run build --prefix frontend` (hoặc `npx vite build`) — pass không lỗi.

## Todo List
- [ ] `DownloadIcon` trong icons.jsx
- [ ] `ImageViewerContext.jsx` (provider + hook)
- [ ] `ImageViewerModal.jsx` (< 200 dòng, Esc/backdrop/X, tải gốc)
- [ ] `image-viewer-modal.css`
- [ ] Bọc provider + import css trong App.jsx
- [ ] Frontend build pass

## Success Criteria
- [ ] Gọi `openViewer({src, filename})` từ component con → modal hiện ảnh full.
- [ ] Đóng được bằng X / click nền / Esc; scroll nền bị khóa lúc mở.
- [ ] Nút "Tải ảnh gốc" tải đúng file với tên gợi ý.
- [ ] Build frontend không lỗi; không vỡ layout canvas.

## Risk Assessment
- **z-index đè SettingsModal/Palette** → đặt z-index cao nhất, test mở đồng thời (hiếm).
- **`download` attr cross-origin bất lực** → URL đều cùng origin (proxy), an toàn. Nếu sau này khác origin: fallback fetch→blob (chưa cần — YAGNI).

## Security Considerations
- Chỉ hiển thị URL nội bộ truyền vào; không nhúng HTML thô.

## Next Steps
- Phase 3 gọi `openViewer` từ mọi điểm hiển thị ảnh + truyền src/filename đúng theo loại node.
