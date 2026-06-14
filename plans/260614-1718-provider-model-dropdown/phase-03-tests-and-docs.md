---
phase: 3
title: Tests and docs
status: completed
priority: P2
effort: 0.25d
dependencies:
  - 1
  - 2
---

# Phase 3: Tests and docs

## Overview

Test catalog + endpoint (mock mạng), verify build frontend + smoke thủ công, cập nhật docs.

## Requirements

- Functional: test offline pass; smoke test dropdown trên UI.
- Non-functional: không key thật trong test; mock network.

## Architecture

**Unit (mock httpx/SDK):**
- `model_catalog.STATIC`: trả đúng list mỗi provider.
- `fetch_live`: mock thành công → parse đúng tên model; mock lỗi → raise.
- Endpoint `POST /api/providers/{provider}/models` (TestClient FastAPI):
  body rỗng → static; provider sai → 400; fetch_live lỗi (monkeypatch raise) → `error` set, 200.

**Manual smoke:**
- ⚙ Cài đặt → đổi provider → static list hiện.
- Nhập key → "⟳ Tải từ API" → live model xuất hiện.
- "Nhập tay" → gõ + lưu → node Tạo ảnh chọn config đó chạy đúng model.

## Related Code Files

- Create: `backend/test_model_catalog.py`
- Read for context: `backend/test_codex.py`, `backend/test_nodes.py` (pattern TestClient/mock)
- Modify: `README.md` (ghi: ô Model giờ là dropdown — static + tải-từ-API + nhập tay)
- Modify: `docs/project-changelog.md` (+ `docs/system-architecture.md` nếu có mục provider/endpoint)

## Implementation Steps

1. `test_model_catalog.py`: test STATIC + `fetch_live` (monkeypatch httpx/genai) + endpoint
   qua `fastapi.testclient.TestClient`. Chạy `backend\.venv\Scripts\python.exe -m pytest`.
2. Sửa tới khi xanh (không bỏ qua fail).
3. README: cập nhật mô tả ⚙ Cài đặt model (dropdown hybrid).
4. `npm run build --prefix frontend` pass.
5. docs-manager cập nhật changelog (+ architecture nếu cần).

## Success Criteria

- [ ] `pytest` backend xanh (gồm test mới, không hồi quy).
- [ ] `npm run build --prefix frontend` pass.
- [ ] README + changelog phản ánh dropdown mới.
- [ ] Smoke thủ công: static + live + nhập tay đều OK.

## Risk Assessment

- **Live API thật khác mock** → smoke thủ công bắt buộc với ít nhất 1 provider (gemini hoặc openai).
- **Test phụ thuộc mạng** → cấm; tất cả mock.
