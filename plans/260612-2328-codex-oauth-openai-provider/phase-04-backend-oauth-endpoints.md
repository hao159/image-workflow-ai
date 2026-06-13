---
phase: 4
title: Backend OAuth Endpoints
status: completed
priority: P1
effort: 3h
dependencies:
  - 2
---

# Phase 4: Backend OAuth Endpoints

## Overview
REST endpoint cho login flow: bắt đầu OAuth (mở browser tới authorize URL), nhận callback đổi token, trả trạng thái login. Dùng OAuth core (Phase 2). Hỗ trợ "cả hai" mode: nếu đã có auth.json thì status báo đã login; chưa thì chạy flow.

## Requirements
- Functional: `GET /api/oauth/openai/status` (đã login? account_id, hết hạn); `POST /api/oauth/openai/start` (trả authorize_url + lưu verifier/state tạm); `GET /auth/callback` (nhận code → exchange → ghi auth.json). Logout (optional).
- Non-functional: chạy local 1 user; verifier/state lưu tạm trong memory process (không cần DB); không lộ token qua API (status chỉ trả masked/account_id).

## Architecture
**Vấn đề redirect_uri cố định cổng 1455:** client_id Codex đăng ký `http://localhost:1455/auth/callback`. Backend chạy cổng 8000 → browser sẽ redirect về `localhost:1455`, KHÔNG phải 8000. 2 lựa chọn:
- **A (giống Codex CLI):** dựng 1 HTTP listener tạm trên cổng 1455 chỉ trong lúc login, bắt callback, lấy code, đóng. Độc lập FastAPI. Khớp redirect_uri đã đăng ký. **Recommend.**
- **B:** đăng ký lại client riêng (không có — dùng client công khai). Loại.

→ Theo A: `POST /api/oauth/openai/start` sẽ: sinh PKCE+state, mở listener cổng 1455 (thread/async, timeout ~120s), mở browser (`webbrowser.open`) tới authorize_url, chờ callback, exchange code, ghi auth.json, trả kết quả. Endpoint này block tới khi xong hoặc timeout (đơn giản, 1 user). Hoặc tách: start trả URL + chạy listener nền, frontend poll status. **Chọn block-until-done** cho KISS (frontend hiện spinner). Nếu muốn non-block, listener nền + poll — ghi chú để cân nhắc.

`session_id`/state: 1 biến module-level giữ verifier hiện tại (1 user, 1 login tại 1 thời điểm).

Listener cổng 1455: dùng `http.server` đơn giản trong thread, hoặc `socket` thô đọc 1 request lấy query `code`. Trả về trang HTML "Đăng nhập thành công, đóng tab này".

## Related Code Files
- Create: `backend/app/oauth_routes.py` — APIRouter cho `/api/oauth/openai/*` + hàm chạy login flow (listener 1455). Tách khỏi main.py để main.py không phình (đang 186 dòng).
- Create: `backend/app/codex_login_server.py` — listener cổng 1455 (callback catcher). Tách riêng vì là concern độc lập (~60-80 dòng).
- Modify: `backend/app/main.py` — `app.include_router(oauth_routes.router)`.
- Modify: `backend/app/main.py` `/api/providers` — thêm trạng thái codex vào `configured` (đã login chưa) nếu hữu ích cho UI.
- Reference: `openai_codex_oauth.py` (Phase 2).

## Implementation Steps
1. `codex_login_server.py`: hàm `wait_for_callback(timeout) -> str` — mở `http.server` trên `("127.0.0.1", 1455)`, handler bắt `GET /auth/callback?code=...&state=...`, lưu code, trả HTML success, shutdown server; trả code (raise nếu timeout/error/state mismatch).
2. `oauth_routes.py`: `router = APIRouter(prefix="/api/oauth/openai")`.
3. `GET /status`: gọi `oauth.read_auth()`; nếu có token → `{logged_in: true, account_id, ...}`; else `{logged_in: false}`. KHÔNG trả token thô.
4. `POST /start`: `generate_pkce()` → `build_authorize_url()`; `webbrowser.open(url)`; `code = wait_for_callback(120)`; `tokens = exchange_code(code, verifier)`; `account_id = account_id_from_id_token(tokens["id_token"])`; `write_auth(...)`; trả `{logged_in: true, account_id}`. Bọc try/except → 400 với message.
5. `POST /logout` (optional, nhỏ): xóa/blank token trong auth.json. Cân nhắc YAGNI — thêm nếu nhanh.
6. `main.py`: include router.
7. Compile check: `python -c "import app.main"` (app-dir backend) + chạy backend, GET `/api/oauth/openai/status` trả 200.

## Todo List
- [ ] codex_login_server.py (listener 1455 + HTML success)
- [ ] oauth_routes.py router + /status
- [ ] /start: PKCE → browser → callback → exchange → write
- [ ] (optional) /logout
- [ ] include_router trong main.py
- [ ] Compile + smoke GET /status

## Success Criteria
- [ ] `GET /api/oauth/openai/status` trả đúng đã/chưa login (không lộ token).
- [ ] `POST /api/oauth/openai/start` mở browser, sau khi user đăng nhập ChatGPT → ghi `~/.codex/auth.json`, trả account_id.
- [ ] Login lại khi đã có token: status báo logged_in true ngay (không cần flow).
- [ ] Cổng 1455 đóng sạch sau khi xong (không leak listener).

## Risk Assessment
- **Cổng 1455 bận** (Codex CLI/đăng nhập khác đang dùng) → bắt lỗi bind, báo "đóng Codex CLI rồi thử lại".
- **Browser không mở được** (headless) → trả authorize_url để user tự mở; ghi chú trong response.
- **Block-until-done timeout** → 120s, báo lỗi rõ; user retry. Nếu UX kém, chuyển sang listener nền + poll (ghi chú).
- **State mismatch / CSRF** → verify state khớp; tool local rủi ro thấp nhưng vẫn check.
