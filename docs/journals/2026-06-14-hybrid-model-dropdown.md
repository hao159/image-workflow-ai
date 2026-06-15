# Hybrid model dropdown for providers — 2026-06-14

## What
Đổi ô Model nhập-tay trong ⚙ Cài đặt thành dropdown hybrid: list curated tĩnh +
nút "⟳ Tải từ API" (fetch live) + option "✎ Nhập tay". Áp dụng mọi provider hiện có.

Commit: `57bd99f`. Plan: `plans/260614-1718-provider-model-dropdown/`.

## Bối cảnh / đổi scope
Brainstorm ban đầu gồm 2 phần: (1) auth Gemini kiểu Codex cho text/vision, (2) dropdown
model. Đã research kỹ phần (1): **Gemini OAuth/Code Assist không sinh ảnh được + vi phạm
ToS reuse creds Gemini CLI** — nên scope xuống "text/vision only" (Path A). Sau đó user
**bỏ hẳn phần auth Gemini**, chỉ giữ dropdown. Plan OAuth (260614-1634-*) đã xóa, lập plan
mới gọn 3 phase.

→ Bài học: research feasibility sớm tránh build nhầm; nhưng quyết định cuối vẫn là cắt scope.

## Thiết kế chốt
- OAuth-vs-key nằm ở cấp named-config/provider (mọi call text/vision đi qua
  `resolve_model_config`) — nhưng phần này đã bỏ.
- Dropdown chỉ là lớp UX; `model_configs.model` vẫn string tự do, không đổi schema.
- Backend: `model_catalog.py` (STATIC dict + `fetch_live`), `POST /api/providers/{provider}/models`
  với `refresh` flag — `False`=static (không chạm mạng), `True`=fetch live soft-fail (HTTP 200 + `error`).
- Frontend: `model-field.jsx` — sentinel `__manual__`, prefill manual khi value lạ, effect chỉ deps `[provider]`.

## Verify
- 9/9 test mới pass (`test_model_catalog.py`), frontend build clean, code-review không Critical/High.
- 2 finding Medium (SSRF qua base_url, raw exception trong `error`) — chấp nhận vì app local
  single-user, base_url vốn đã user-controlled.

## Gotchas
- `pytest` thiếu trong `backend/.venv` → đã cài.
- `test_engine_cache.py` fail 8 test **có sẵn từ trước** (xác nhận qua git stash) — không phải
  do thay đổi này; là vấn đề test-isolation/pytest-runner cần soi riêng.
