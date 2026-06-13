---
title: 'Image viewer modal, download original, fix upload duplicate preview'
description: >-
  Lightbox modal khi click ảnh ở các node hiển thị ảnh + nút tải ảnh gốc; bỏ ảnh
  trùng trên node Tải ảnh lên
status: completed
priority: P2
branch: ''
tags:
  - frontend
  - backend
  - ux
blockedBy: []
blocks: []
created: '2026-06-13T07:12:53.753Z'
createdBy: 'ck:plan'
source: skill
---

# Image viewer modal, download original, fix upload duplicate preview

## Overview

2 yêu cầu UX cho các node hiển thị ảnh (Tải ảnh lên / Tạo-Sửa ảnh AI / Lưu ảnh + node Biến đổi):

1. **Bỏ ảnh trùng** — node `load_image` đang hiện 2 ảnh: 1 trong ô upload (param) + 1 ở khối preview dưới (sau khi chạy). Giữ ô upload, bỏ khối preview cho node này.
2. **Modal xem ảnh + tải ảnh gốc** — click ảnh bất kỳ trong node → mở lightbox xem ảnh full-res + nút "Tải ảnh gốc".

**Vấn đề cốt lõi (đã verify):** `preview` gửi về frontend là **thumbnail JPEG downscale** (`engine.py:19-24`, `PREVIEW_MAX`, quality 80), KHÔNG phải ảnh gốc. Ảnh gốc (PNG full-res) của node AI/Biến đổi chỉ nằm trong cache blob backend (`cache.py`, content-addressed theo sha256), không expose qua URL. Upload (`/api/uploads/{id}`) và Lưu ảnh (`/api/outputs/{name}`) đã có URL gốc sẵn. → Cần endpoint backend phục vụ ảnh gốc từ cache blob cho node AI/Biến đổi.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Backend original-image endpoint](./phase-01-backend-original-image-endpoint.md) | Completed |
| 2 | [Image viewer modal + context](./phase-02-image-viewer-modal-context.md) | Completed |
| 3 | [Wire image displays + fix upload duplicate](./phase-03-wire-image-displays-fix-upload-duplicate.md) | Completed |

## Key Decisions

- **Tải ảnh gốc cho node AI/Biến đổi** → endpoint `GET /api/cache-image/{sha}` phục vụ `cache/blobs/{sha}.bin` (PNG). `_meta()` thêm field `sha` cho output ảnh. Lý do: `preview` chỉ là thumbnail, "ảnh gốc" yêu cầu full-res.
- **Modal dùng React Context** (giống `RunContext`) — `ImageUploadField` nằm sâu (App→ReactFlow→WorkflowNode→NodeParamField→ImageUploadField), không prop-drill qua ReactFlow được. 1 modal duy nhất render ở App.
- **Tải file:** thẻ `<a download>` (cùng origin qua proxy Vite). Filename gợi ý theo node title / tên file.

## Dependencies

- Phase 2 độc lập Phase 1. Phase 3 cần cả 1 (sha→URL gốc cho node AI) và 2 (modal + context).
- Không trùng 3 plan đang mở (codex-oauth / prompt-supplement / per-node-cache).
