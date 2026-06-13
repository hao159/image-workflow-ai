---
phase: 2
title: OAuth Core Module
status: completed
priority: P1
effort: 3h
dependencies:
  - 1
---

# Phase 2: OAuth Core Module

## Overview
Module thuần (không phụ thuộc FastAPI/web) lo toàn bộ OAuth Codex: PKCE, dựng URL authorize, đổi code→token, refresh token, đọc/ghi `~/.codex/auth.json`, giải `account_id` từ `id_token`. Là nền cho provider (Phase 3) và endpoint (Phase 4).

## Requirements
- Functional: lấy được `access_token` + `account_id` hợp lệ; tự refresh khi sắp hết hạn; persist lại file; dựng URL authorize + verifier cho login flow.
- Non-functional: KISS, dưới 200 dòng; không log token; xử lý lỗi rõ ràng (file hỏng, refresh fail).

## Architecture
Hằng số (research §3):
- `CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"`
- `AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"`
- `TOKEN_URL = "https://auth.openai.com/oauth/token"`
- `REDIRECT_URI = "http://localhost:1455/auth/callback"` (cố định theo client_id)
- `AUTH_FILE = Path.home() / ".codex" / "auth.json"` (đường dẫn mặc định Codex CLI)
- `SCOPE = "openid profile email offline_access"`
- Extra authorize params: `id_token_add_organizations=true`, `codex_cli_simplified_flow=true`, `originator=codex_cli_rs`.

`auth.json` cấu trúc Codex CLI (tham khảo): `{ "OPENAI_API_KEY": null, "tokens": { "access_token", "refresh_token", "id_token", "account_id" }, "last_refresh": "<iso>" }`. **Verify cấu trúc thật lúc implement** — đọc file mẫu nếu user đã `codex login`; nếu khác, adapt parser. Module nên đọc linh hoạt (chấp nhận cả token ở root lẫn trong `tokens`).

Hàm chính:
- `generate_pkce() -> (verifier, challenge)` — verifier random urlsafe 64 byte; challenge = base64url(sha256(verifier)) no padding.
- `build_authorize_url(verifier, state) -> str` — ráp query params.
- `exchange_code(code, verifier) -> dict` — POST TOKEN_URL grant_type=authorization_code; trả tokens.
- `refresh_tokens(refresh_token) -> dict` — POST grant_type=refresh_token.
- `account_id_from_id_token(id_token) -> str` — decode JWT payload (base64url phần giữa, không cần verify chữ ký vì local), lấy claim chứa account/org id (vd `https://api.openai.com/auth` → `chatgpt_account_id`). **Verify claim path thật.**
- `read_auth() -> dict | None` / `write_auth(tokens)` — IO file, tạo thư mục nếu thiếu.
- `get_valid_access_token() -> (access_token, account_id)` — đọc file; nếu token sắp hết hạn (<5 phút) hoặc thiếu → refresh; persist; trả về. Raise nếu không có gì để refresh (chưa login).

Refresh-expiry: nếu auth.json có `expires_at`/`last_refresh` thì dùng; nếu không có timestamp đáng tin, thử request và refresh khi 401 (lazy refresh — robust hơn việc đoán expiry).

## Related Code Files
- Create: `backend/app/providers/openai_codex_oauth.py` (module thuần, ~150-180 dòng; nếu vượt 200 tách helper JWT/IO).
- Modify: `backend/app/config.py` — thêm `CODEX_AUTH_FILE` path const (cho dễ override/test), reuse `Path.home()`.
- Dùng `httpx` (đã là dep gián tiếp? check `requirements.txt`; nếu chưa có, thêm `httpx`). Token POST đồng bộ (`httpx.post`) — module sync, khớp engine chạy thread pool.

## Implementation Steps
1. Check `backend/requirements.txt` có `httpx` chưa; nếu chưa, thêm và `pip install`.
2. Tạo `openai_codex_oauth.py` với hằng số + các hàm trên.
3. `generate_pkce`: `secrets.token_urlsafe(64)`; challenge sha256 → base64url strip `=`.
4. `build_authorize_url`: urlencode đầy đủ params (client_id, response_type=code, redirect_uri, scope, code_challenge, code_challenge_method=S256, state, 3 extra params).
5. `exchange_code` / `refresh_tokens`: httpx POST form-encoded; parse JSON; raise `ProviderError`-friendly khi non-2xx.
6. `account_id_from_id_token`: split `.`, base64url-decode phần [1], json.loads, dò claim account id (thử các path biết được, log nếu không thấy).
7. `read_auth`/`write_auth`: json IO, `ensure_ascii=False`, tạo `~/.codex/` nếu thiếu; chỉ ghi đè field tokens, giữ field khác.
8. `get_valid_access_token`: logic đọc → (refresh nếu cần) → trả `(access_token, account_id)`. Hỗ trợ lazy-refresh callback cho provider dùng khi gặp 401.
9. Compile check: `python -c "from app.providers import openai_codex_oauth as m; print(m.build_authorize_url('v','s'))"` (app-dir backend).

## Todo List
- [ ] httpx có trong requirements
- [ ] Hằng số + skeleton module
- [ ] PKCE generate
- [ ] build_authorize_url
- [ ] exchange_code + refresh_tokens
- [ ] account_id_from_id_token (verify claim path)
- [ ] read/write auth.json (verify cấu trúc thật)
- [ ] get_valid_access_token (+ lazy refresh)
- [ ] Compile check

## Success Criteria
- [ ] `build_authorize_url` ra URL đúng định dạng (mở browser tới được trang login OpenAI).
- [ ] Nếu đã có `~/.codex/auth.json` hợp lệ → `get_valid_access_token()` trả token + account_id không lỗi.
- [ ] Refresh chạy được khi token cũ (hoặc khi 401 lazy-refresh).
- [ ] Không có token nào bị log ra stdout.

## Risk Assessment
- **Cấu trúc auth.json / claim account_id khác giả định** → đọc linh hoạt + verify file thật; đây là rủi ro chính, ưu tiên test sớm nếu user đã `codex login`.
- **Endpoint/params OpenAI đổi** → giá trị từ research mới nhất; nếu authorize trả lỗi, đối chiếu Codex CLI bản cài trên máy.
