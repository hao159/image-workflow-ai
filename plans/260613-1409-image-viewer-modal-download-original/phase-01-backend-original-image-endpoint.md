---
phase: 1
title: Backend original-image endpoint
status: completed
priority: P2
effort: 1h
dependencies: []
---

# Phase 1: Backend original-image endpoint

## Overview
Expose ảnh gốc full-res của node AI/Biến đổi qua URL để frontend xem + tải. Hiện chỉ có thumbnail preview; bytes gốc nằm trong cache blob (`cache/blobs/{sha}.bin`) không có endpoint.

## Key Insights
- `engine._meta()` (`backend/app/engine.py:50-58`) gửi metadata output về UI: image → `{dtype:'image', size}`. Thiếu định danh để lấy bytes gốc.
- Cache lưu ảnh content-addressed: `blobs/{sha}.bin`, `sha = sha256(bytes)` (`cache.py:75-79`).
- Thứ tự ở miss-path: `cache.save()` (ghi blob) **trước** `emit(node_finished, outputs=_meta(...))` (`engine.py:155-158`) → khi `_meta` chạy, blob đã tồn tại. Hit-path dùng `cached.outputs` (đọc từ blob) nên sha cũng khớp.
- Path-serving an toàn có tiền lệ: `/api/uploads/{name}`, `/api/outputs/{name}` trong `main.py` (dùng làm mẫu guard).

## Requirements
- Functional: `GET /api/cache-image/{sha}` trả bytes blob, `Content-Type: image/png`. `_meta` thêm `sha` cho output ảnh.
- Non-functional: chặn path traversal (validate sha là hex 64 ký tự); blob đã evict → 404 rõ ràng, không 500.

## Architecture
```
node AI chạy → outputs{handle: PNG bytes}
  ├─ cache.save() → blobs/{sha}.bin
  └─ _meta() → {dtype:'image', size, sha}  ──WS──▶ frontend lưu vào data.outputs
frontend click ảnh → GET /api/cache-image/{sha} → FileResponse(blobs/{sha}.bin, image/png)
```

## Related Code Files
- Modify: `backend/app/engine.py` — `_meta()` thêm `sha` (cần `import hashlib`).
- Modify: `backend/app/main.py` — thêm route `GET /api/cache-image/{sha}`.
- Read context: `backend/app/cache.py` (layout blob), `backend/app/config.py` (`CACHE_DIR`).

## Implementation Steps
1. `engine._meta()`: trong nhánh `isinstance(value, bytes)`, thêm `"sha": hashlib.sha256(value).hexdigest()` vào dict. Thêm `import hashlib` đầu file nếu chưa có.
2. `main.py`: thêm endpoint:
   ```python
   @app.get("/api/cache-image/{sha}")
   def cache_image(sha: str):
       if not re.fullmatch(r"[0-9a-f]{64}", sha):
           raise HTTPException(404)
       path = (config.CACHE_DIR / "blobs" / f"{sha}.bin").resolve()
       if not path.is_relative_to(config.CACHE_DIR) or not path.exists():
           raise HTTPException(404, "Ảnh gốc không còn trong cache (đã bị dọn).")
       return FileResponse(path, media_type="image/png")
   ```
   (dùng `re`, `HTTPException`, `FileResponse` — kiểm tra import sẵn có trong main.py, thêm nếu thiếu).
3. Compile-check backend: `backend\.venv\Scripts\python.exe -c "import app.main, app.engine"` (chạy trong `backend/`).

## Todo List
- [ ] `_meta()` thêm `sha` + import hashlib
- [ ] Endpoint `/api/cache-image/{sha}` với guard hex + path + 404
- [ ] Import check (`re`, `HTTPException`, `FileResponse`) trong main.py
- [ ] Compile-check backend pass

## Success Criteria
- [ ] Node AI chạy → WS `node_finished.outputs[handle]` có field `sha` (64 hex).
- [ ] `GET /api/cache-image/{sha hợp lệ}` trả PNG bytes đúng = blob.
- [ ] sha sai định dạng / blob không tồn tại → 404 (không 500, không lộ path).
- [ ] Backend import không lỗi.

## Risk Assessment
- **Blob evict giữa run và click tải** (`CACHE_MAX_BYTES`) → 404. Mitigation: thông báo lỗi rõ; frontend bắt 404. Hiếm (ảnh vừa sinh = blob mới nhất, evict cũ nhất trước).
- **Endpoint công khai theo sha** — chỉ đoán được nếu biết sha256 (không liệt kê được). Tool cá nhân/local → chấp nhận; không thêm auth (YAGNI).

## Security Considerations
- Path traversal: regex hex 64 + `is_relative_to(CACHE_DIR)` chặn `../`.
- Không log sha như bí mật (không phải secret).

## Next Steps
- Phase 3 dùng `outputs[handle].sha` dựng URL `/api/cache-image/{sha}` cho node AI/Biến đổi.
