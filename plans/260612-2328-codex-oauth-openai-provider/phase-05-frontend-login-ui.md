---
phase: 5
title: Frontend Login UI
status: completed
priority: P2
effort: 2h
dependencies:
  - 1
  - 4
---

# Phase 5: Frontend Login UI

## Overview
Thêm provider "OpenAI (Codex)" vào SettingsModal, nút "Đăng nhập OpenAI", hiển thị trạng thái login (account_id), ẩn ô API key khi provider=codex. Thêm hàm API gọi endpoint OAuth.

## Requirements
- Functional: tạo config provider "codex" không cần api_key; nút login gọi `/api/oauth/openai/start`; hiện trạng thái đã/chưa login; sau login refresh status; config codex dùng được trong node.
- Non-functional: nhất quán UI hiện có (SettingsModal style), tiếng Việt.

## Architecture
- `SettingsModal.PROVIDERS`: thêm `{ value: 'codex', label: 'OpenAI (Codex OAuth)', defaultModel: 'gpt-5.5' }`. (3 provider cũ vẫn ở đây — đây là list để TẠO config, khác với "3 provider thô trong dropdown node" đã xóa ở Phase 1. KHÔNG nhầm.)
- Khi `form.provider === 'codex'`: ẩn ô API key (như comfyui ẩn key, hiện base_url). Thay vào hiện: trạng thái login + nút "Đăng nhập OpenAI". Config codex chỉ cần `name` + `model` (model ảnh, vd gpt-image-1 hoặc để trống).
- `api.js`: thêm `getOpenAIOAuthStatus()`, `startOpenAIOAuth()`.
- SettingsModal load status lúc mở (useEffect) + sau khi login xong.
- Login flow UX: bấm nút → gọi `startOpenAIOAuth()` (backend mở browser, block tới khi xong) → spinner → thành công refresh status. Báo lỗi nếu fail.

## Related Code Files
- Modify: `frontend/src/components/SettingsModal.jsx` — PROVIDERS thêm codex; render nhánh codex (ẩn api_key, hiện login UI + status); import API mới.
- Modify: `frontend/src/api.js` — `getOpenAIOAuthStatus`, `startOpenAIOAuth`.
- Reference: `frontend/src/App.jsx` (refreshNodeTypes sau onChanged — đã có), `WorkflowNode.jsx` (Phase 1 đã guard options).
- (CSS) `frontend/src/styles.css` hoặc `styles/` — class nhỏ cho login status/badge nếu cần (giữ tối thiểu).

## Implementation Steps
1. `api.js`: thêm
   ```js
   export async function getOpenAIOAuthStatus() {
     const res = await fetch('/api/oauth/openai/status'); return res.json()
   }
   export async function startOpenAIOAuth() {
     const res = await fetch('/api/oauth/openai/start', { method: 'POST' })
     const body = await res.json().catch(() => ({}))
     if (!res.ok) throw new Error(body.error || 'Đăng nhập thất bại.')
     return body
   }
   ```
2. SettingsModal: thêm codex vào PROVIDERS.
3. State `oauthStatus` + `loggingIn`; `useEffect` load status khi mở modal.
4. Render: `form.provider === 'codex'` → block hiện: nếu logged_in → "✓ Đã đăng nhập (account: …)"; else nút "🔑 Đăng nhập OpenAI". Ẩn ô api_key (đổi điều kiện `form.provider !== 'comfyui'` → `!== 'comfyui' && !== 'codex'`).
5. Nút login: `setLoggingIn(true)` → `startOpenAIOAuth()` → reload status → `setLoggingIn(false)`; catch → setErrorMsg.
6. Submit config codex: api_key gửi rỗng (OK, provider codex không dùng). Đảm bảo backend `/api/model-configs` chấp nhận provider="codex" — đã chấp nhận vì PROVIDER_NAMES chứa codex sau Phase 3 (validate `cfg.provider not in PROVIDER_NAMES`). **Verify PROVIDER_NAMES gồm codex** (Phase 3 thêm vào PROVIDER_CLASSES → PROVIDER_NAMES tự có).
7. Build check: `npm run build --prefix frontend` hoặc dev không lỗi.

## Todo List
- [ ] api.js: getOpenAIOAuthStatus + startOpenAIOAuth
- [ ] PROVIDERS thêm codex
- [ ] oauthStatus state + load khi mở modal
- [ ] Ẩn api_key cho codex, hiện login UI + status
- [ ] Nút đăng nhập + spinner + error
- [ ] Tạo config codex lưu được
- [ ] Build check

## Success Criteria
- [ ] Mở ⚙ Cài đặt model → chọn provider "OpenAI (Codex OAuth)" → thấy nút đăng nhập / trạng thái.
- [ ] Bấm đăng nhập → browser mở → sau khi login thành công → UI báo đã đăng nhập.
- [ ] Tạo được config codex (vd "OpenAI Codex - Image"), xuất hiện trong dropdown node.
- [ ] Node Tạo ảnh chọn config codex → chạy ra ảnh (phụ thuộc Phase 3 + token).

## Risk Assessment
- **Block-until-done login** → frontend spinner có thể "treo" tới 120s nếu user chần chừ; hiển thị hint "Hoàn tất đăng nhập trên trình duyệt". Nếu khó chịu → chuyển poll-status (gắn với QĐ Phase 4).
- **Nhầm "xóa provider"**: PROVIDERS trong SettingsModal (list tạo config) KHÁC provider thô trong dropdown node (đã xóa Phase 1). Không xóa nhầm.
