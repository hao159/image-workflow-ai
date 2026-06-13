# Research Report: Đăng nhập OpenAI qua Codex OAuth + dọn config/model UI

> Thời điểm research: 2026-06-12 23:16 (+07). Ngôn ngữ: tiếng Việt, văn phong cô đọng (hy sinh ngữ pháp).

## Mục lục
1. Executive Summary
2. Phạm vi & 3 hạng mục user yêu cầu
3. Codex OAuth — cơ chế kỹ thuật
4. Dùng model OpenAI qua OAuth (gồm tạo ảnh)
5. ⚠️ Rủi ro lớn nhất: edit ảnh + ToS + Responses API
6. Map vào codebase hiện tại
7. Khuyến nghị kiến trúc (provider mới `codex`)
8. Khuyến nghị task 2 & 3 (xóa config mặc định + bỏ ô model)
9. Implementation outline
10. Nguồn tham khảo
11. Câu hỏi chưa giải đáp

---

## 1. Executive Summary

User muốn: (a) đăng nhập OpenAI bằng OAuth của Codex ("Sign in with ChatGPT") để xài model OpenAI qua subscription thay vì API key; (b) xóa 3 config provider mặc định trong dropdown node; (c) bỏ ô nhập "Model" trong node.

**Khả thi — nhưng có cạm bẫy kiến trúc.** Codex OAuth dùng PKCE chuẩn, endpoint `auth.openai.com`, token lưu `~/.codex/auth.json`, tự refresh. Sau khi có token, **không gọi được** `api.openai.com/v1/images/generate` (SDK hiện tại) — phải gọi `chatgpt.com/backend-api/codex/responses` (**Responses API**, định dạng request/SSE hoàn toàn khác) kèm header `chatgpt-account-id`. Tạo ảnh qua đây xài tool `{"type":"image_generation"}`, server trả base64 PNG qua SSE.

**Kết luận thực thi:** không sửa `openai_provider.py` (SDK key) thành OAuth — mà **thêm provider mới** (`codex` / `openai-codex`) chạy Responses API + auth riêng. Provider OpenAI cũ (API key) giữ nguyên làm fallback. Edit ảnh qua OAuth **chưa chắc chắn** — cần verify lúc implement (xem §5).

Task 2 & 3 (xóa default config + bỏ ô model) đơn giản, độc lập backend ~2-3 chỗ + frontend 1 chỗ.

---

## 2. Phạm vi & 3 hạng mục

| # | Yêu cầu user | Bản chất | Độ phức tạp |
|---|---|---|---|
| 1 | Đăng nhập OpenAI qua OAuth Codex để xài model OpenAI | Thêm auth flow + provider mới gọi Responses API | **Cao** |
| 2 | "Xóa 3 cái config mặc định" | Bỏ `PROVIDER_NAMES` thô (gemini/openai/comfyui) khỏi dropdown node | Thấp |
| 3 | "Bỏ chổ nhập modal trong node" (model) | Xóa `Param("model", ...)` ở node generate/edit | Thấp |

Hiểu task 2: hiện `provider_options()` = `[tên config] + ["gemini","openai","comfyui"]`. 3 cái sau là "config mặc định" thô (xài key .env). User muốn dropdown chỉ còn config tự đặt tên.

Hiểu task 3: model hiện vào từ 2 chỗ — ô "Model khác" trong node **và** field model trong config. User muốn bỏ ô trong node → model chỉ lấy từ config. Gọn UX: mỗi config = provider + model + credentials, node chỉ chọn 1 config.

---

## 3. Codex OAuth — cơ chế kỹ thuật

Flow `codex login` ("Sign in with ChatGPT"):

```
1. Backend mở local HTTP server cổng 1455 (bắt callback)
2. Sinh PKCE: code_verifier + code_challenge (S256)
3. Mở browser → https://auth.openai.com/oauth/authorize
   ?client_id=app_EMoamEEZ73f0CkXaXp7hrann
   &response_type=code
   &redirect_uri=http://localhost:1455/auth/callback
   &scope=openid profile email offline_access
   &code_challenge=...&code_challenge_method=S256
   &id_token_add_organizations=true
   &codex_cli_simplified_flow=true
   &originator=codex_cli_rs   (Codex CLI; proxy bên thứ 3 dùng "opencode")
   &state=<random>
4. User đăng nhập ChatGPT → redirect về localhost:1455 kèm ?code=
5. POST https://auth.openai.com/oauth/token
   grant_type=authorization_code, code, code_verifier, client_id, redirect_uri
   → { access_token, refresh_token, id_token, expires_in }
6. account_id giải mã từ claim trong id_token (JWT)
7. Lưu ~/.codex/auth.json (plaintext)
```

**Quan trọng:** `client_id` công khai `app_EMoamEEZ73f0CkXaXp7hrann` đăng ký cứng `redirect_uri = http://localhost:1455/auth/callback`. Muốn tái dùng client_id này thì **bắt buộc** cổng 1455 + path `/auth/callback`.

**Refresh:** token tự refresh khi còn <5 phút hết hạn → POST `token` endpoint với `grant_type=refresh_token`. Refresh token xài lâu dài, persist lại file.

**Tái dùng vs login mới:**
- *MVP (KISS):* đọc thẳng `~/.codex/auth.json` nếu user đã chạy `codex login` từ trước. Không cần dựng OAuth server.
- *Đầy đủ (user yêu cầu "đăng nhập"):* implement flow trên trong backend, nút "Đăng nhập OpenAI" trên UI.

---

## 4. Dùng model OpenAI qua OAuth (gồm tạo ảnh)

Sau khi có `access_token` + `account_id`, **KHÔNG** dùng `api.openai.com`. Phải gọi:

```
POST https://chatgpt.com/backend-api/codex/responses
Headers:
  Authorization: Bearer <access_token>
  chatgpt-account-id: <account_id>
  OpenAI-Beta: responses=experimental
  originator: codex_cli_rs
  session_id: <uuid>            (mỗi request/phiên)
  version: <codex version>
  Content-Type: application/json
Body (Responses API, KHÁC chat/completions):
{
  "model": "gpt-5.5",                          // model coding; tool tự chọn gpt-image nội bộ
  "tools": [{"type": "image_generation"}],
  "input": [{"role":"user","content":[{"type":"input_text","text":"<prompt>"}]}],
  "stream": true
}
```

**Response = SSE stream**, các phase:
```
response.image_generation_call.in_progress   → queued
response.image_generation_call.generating    → generating
response.image_generation_call.partial_image → preview tiến độ (optional)
response.output_item.done                    → item.type=="image_generation_call",
                                               item.result = base64 PNG  ← LẤY Ở ĐÂY
```

- **Size verify được:** `1024x1024`, `1024x1536`, `1536x1024` (giống gpt-image). Size lớn hơn forward thẳng, backend tùy tier.
- **Model ảnh:** qua OAuth, gpt-image-1 / gpt-image-1.5 / gpt-image-2 chọn được; quality do model tự quyết (không control như API key path).
- **Endpoint dạng `/v1/...`:** vài proxy expose `/v1/responses`, `/v1/chat/completions`, `/v1/models` (text). Ảnh đi qua tool image_generation trong responses.

---

## 5. ⚠️ Rủi ro lớn nhất

### 5.1 Edit ảnh qua OAuth — CHƯA CHẮC
- Project hiện có `OpenAIProvider.edit()` gọi `images.edit` (SDK, API key). **Endpoint codex/responses không expose `/v1/images/edits`** (xác nhận ở proxy chatgpt-imagegen: "image edits ❌ not exposed yet").
- *Khả năng vẫn làm được:* Responses API cho phép truyền `input_image` (base64/URL) trong `content` cùng tool `image_generation` → model edit ảnh input. Đây là cơ chế multimodal chuẩn của Responses API, **nhiều khả năng chạy** nhưng **phải test thực tế** với token OAuth lúc implement.
- *Quyết định:* nếu edit qua OAuth fail → giữ `edit()` đi đường API key (provider openai cũ), chỉ `generate()` đi OAuth. Hoặc báo user node Sửa ảnh chưa support provider codex.

### 5.2 Vi phạm ToS OpenAI
- Mọi proxy đều cảnh báo: token = "password-equivalent", **không** host service, **không** share/pool token. Tái dùng `client_id` của Codex + endpoint nội bộ ChatGPT là vùng xám ToS. Tool local 1 user → rủi ro thấp; nhưng cần user hiểu đây không phải API chính thức, OpenAI có thể đổi endpoint/chặn bất cứ lúc nào.

### 5.3 Responses API ≠ SDK hiện tại
- Không tái dùng được `from openai import OpenAI; client.images.generate(...)`. Phải tự viết HTTP + SSE parser (httpx/sse). Đây là phần code mới chính.

---

## 6. Map vào codebase hiện tại

| File | Vai trò | Tác động |
|---|---|---|
| `backend/app/providers/openai_provider.py` | OpenAI SDK + API key | **Giữ nguyên** (fallback). KHÔNG nhét OAuth vào đây |
| `backend/app/providers/base.py` | `ImageProvider` interface (generate/edit) | Provider mới kế thừa interface này |
| `backend/app/providers/__init__.py` | `PROVIDER_CLASSES`, `provider_options()`, `resolve_model_config()` | Thêm `codex`; **sửa `provider_options()` (task 2)** |
| `backend/app/db.py` | bảng `model_configs` (name/provider/api_key/model/base_url) | Cần chỗ lưu OAuth token (xem §7) |
| `backend/app/config.py` | env keys | Thêm path `~/.codex/auth.json`, oauth consts |
| `backend/app/main.py` | REST endpoints, `/api/providers` | Thêm endpoint OAuth login/status; bỏ raw providers nếu cần |
| `backend/app/nodes/generate.py` & `edit.py` | Param provider/model | **Bỏ `Param("model")` (task 3)** |
| `frontend/src/components/SettingsModal.jsx` | form config, `PROVIDERS` list | Thêm provider "codex" + nút Đăng nhập; xử lý không-cần-api_key |
| `frontend/src/components/WorkflowNode.jsx` | render form node | Tự cập nhật khi backend bỏ param model |

---

## 7. Khuyến nghị kiến trúc (provider mới `codex`)

**Provider mới** `OpenAICodexProvider` (`backend/app/providers/openai_codex.py`), register key `codex`:

```python
class OpenAICodexProvider(ImageProvider):
    name = "codex"
    # __init__: nhận access_token + account_id (hoặc đọc auth.json)
    # _ensure_token(): refresh nếu sắp hết hạn
    # generate(): POST chatgpt.com/backend-api/codex/responses, parse SSE → base64 → bytes
    # edit(): thử input_image trong content; nếu backend từ chối → ProviderError rõ ràng
```

**Lưu token — 2 lựa chọn:**
- **A (KISS, recommend MVP):** đọc/ghi `~/.codex/auth.json` y như Codex CLI. Tự refresh, persist lại. User nào đã `codex login` thì xài ngay; chưa thì backend chạy flow §3 ghi vào file đó.
- **B:** bảng `oauth_tokens` riêng trong SQLite (access/refresh/account_id/expires_at). Sạch hơn, không đụng file Codex CLI, nhưng phải tự implement toàn bộ login flow.

→ Đề xuất **A** cho MVP (tận dụng `codex login` có sẵn nếu user đã cài Codex CLI), kèm endpoint backend tự chạy OAuth nếu file chưa có.

**`resolve_model_config()`**: config provider="codex" không cần api_key. Field `model` của config = model ảnh muốn dùng (vd `gpt-image-1`), default nếu trống.

**Endpoint mới `main.py`:**
- `POST /api/oauth/openai/start` → khởi động flow, trả URL authorize (hoặc tự mở browser)
- `GET /api/oauth/openai/callback` → nhận code, đổi token, lưu
- `GET /api/oauth/openai/status` → đã login chưa, account_id, hết hạn khi nào

---

## 8. Khuyến nghị task 2 & 3

### Task 2 — Xóa 3 config mặc định
`providers/__init__.py`:
```python
def provider_options() -> list[str]:
    return [c["name"] for c in db.list_model_configs()]   # bỏ "+ PROVIDER_NAMES"
```
- `resolve_model_config()`: bỏ nhánh fallback `if selection in PROVIDER_CLASSES` (hoặc giữ cho tương thích workflow cũ nhưng không hiện trong dropdown).
- Hệ quả: dropdown rỗng nếu chưa tạo config → cần default UX (vd auto-tạo 1 config mẫu, hoặc thông báo "Mở ⚙ Cài đặt model"). **Cần xác nhận user muốn xử lý ra sao.**
- `default="gemini"` ở `Param("provider")` không còn hợp lệ → đổi default thành "" hoặc config đầu tiên.

### Task 3 — Bỏ ô model trong node
`generate.py` & `edit.py`: xóa dòng
```python
Param("model", "text", "Model khác (bỏ trống = theo cấu hình)", default=""),
```
- `run()`: bỏ `params.get("model") or`, chỉ còn `model=default_model` (từ config).
- UI tự cập nhật (form sinh từ metadata). Workflow cũ có param model dư → engine bỏ qua, không lỗi.

---

## 9. Implementation outline (đề xuất thứ tự)

1. **Task 2 + 3 trước** (độc lập, nhanh, ít rủi ro): sửa `provider_options`, 2 node, default provider, SettingsModal.
2. **OAuth core:** module `openai_codex_oauth.py` (PKCE, authorize URL, token exchange, refresh, đọc/ghi auth.json).
3. **Provider `codex`:** `openai_codex.py` (generate qua Responses API + SSE parser). Register vào `PROVIDER_CLASSES`.
4. **Verify edit** qua OAuth (input_image). Pass/fail → quyết định §5.1.
5. **Backend endpoints** OAuth start/callback/status.
6. **Frontend:** nút "Đăng nhập OpenAI (Codex)" trong SettingsModal, provider "codex" (ẩn ô API key), hiển thị status login.
7. Test e2e (`backend/test_e2e.py` cần backend chạy).

---

## 10. Nguồn tham khảo

- [Authentication – Codex | OpenAI Developers](https://developers.openai.com/codex/auth) — flow OAuth chính thức
- [Codex CLI Authentication flows (danielvaughan)](https://codex.danielvaughan.com/2026/04/01/codex-cli-authentication-flows-credential-management/) — chi tiết PKCE, port 1455, client_id, auth.json
- [The Codex Subscription API (danielvaughan)](https://codex.danielvaughan.com/2026/04/24/codex-subscription-api-programmatic-access-gpt-5-5-chatgpt-plan/) — endpoint codex/responses, model
- [EvanZhouDev/openai-oauth](https://github.com/EvanZhouDev/openai-oauth/) — proxy OAuth→OpenAI-compatible, default client_id/token-url, giới hạn (text-only, không image)
- [leeguooooo/chatgpt-imagegen](https://github.com/leeguooooo/chatgpt-imagegen) — **tạo ảnh** qua codex/responses: request body, SSE phases, size, edit chưa support (MIT)
- [icebear0828/codex-proxy](https://github.com/icebear0828/codex-proxy), [wowyuarm/codex-proxy](https://github.com/wowyuarm/codex-proxy), [router-for-me/CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) — tham khảo proxy Responses API
- [OpenClaw image-generation docs](https://docs.openclaw.ai/tools/image-generation) + [issue #71179](https://github.com/openclaw/openclaw/issues/71179) — image_generation tool qua Codex OAuth, gpt-image-1/1.5/2, payload `image_generation_call`
- [7shi/codex-oauth](https://github.com/7shi/codex-oauth) — sample implement OAuth WHAM backend

---

## 11. Quyết định đã chốt với user (2026-06-12)

1. **Login mode → CẢ HAI:** backend đọc `~/.codex/auth.json` nếu có; chưa có thì chạy full OAuth flow (PKCE + callback cổng 1455, nút "Đăng nhập OpenAI" trong UI). Lựa chọn A+B ở §7.
2. **Edit ảnh → CỨ THỬ `input_image`:** implement edit qua `input_image` trong Responses API; nếu test token thật fail mới quyết định fallback. Không chặn trước.
3. **Dropdown rỗng → BÁO "Mở ⚙ Cài đặt model":** xóa hẳn 3 provider thô khỏi dropdown; khi DB chưa có config nào thì node hiển thị thông báo hướng dẫn mở Cài đặt model (không auto-seed, không fallback ẩn).
4. **ToS → OK:** tool local cá nhân 1 máy, không host/share/pool token. Tiếp tục implement.

### Suy ra từ quyết định:
- **Task 2:** `provider_options()` bỏ hẳn `+ PROVIDER_NAMES`. `resolve_model_config()` bỏ nhánh fallback provider thô → chọn provider thô sẽ báo lỗi rõ "config không tồn tại" (chấp nhận, vì dropdown không còn hiện chúng). Workflow cũ lưu provider="gemini" thô → sẽ lỗi khi chạy, cần user tạo config tên tương ứng (chấp nhận theo QĐ #3).
- **`Param("provider")` default:** đổi từ `"gemini"` → `""` (rỗng); node báo thiếu config nếu chưa chọn.

### Còn phải verify lúc implement (không phải câu hỏi cho user):
- Edit qua `input_image` có chạy trên `codex/responses` không (test token thật).
- Header chính xác cần cho image_generation (originator/session_id/version) — đối chiếu Codex CLI mới nhất lúc code.

---

## 12. KẾT QUẢ IMPLEMENT (cập nhật 2026-06-12, sau khi code xong)

Đã code + verify (plan `plans/260612-2328-codex-oauth-openai-provider/`). Empirical findings từ máy thật (Codex CLI 0.47.0 cài sẵn, `~/.codex/auth.json` tồn tại):

- **Cấu trúc auth.json XÁC NHẬN:** `{auth_mode:"chatgpt", OPENAI_API_KEY:null, tokens:{id_token, access_token, refresh_token, account_id}, last_refresh}`. → `account_id` lấy THẲNG từ `tokens.account_id` (không cần decode JWT khi đọc file).
- **account_id cho login mới:** claim `https://api.openai.com/auth`.`chatgpt_account_id` trong id_token (đã verify path).
- **access_token là JWT có `exp`** → dùng để tính hết hạn (refresh khi còn <5 phút).
- **⚠ refresh_token XOAY (rotation):** gọi refresh với token đã dùng → HTTP 401 `code:"refresh_token_reused"`. Verify: format request của ta ĐÚNG (cả form lẫn JSON đều ra cùng lỗi semantic). → mỗi refresh thành công PHẢI persist refresh_token mới (đã làm trong `store_login`). Hệ quả: token trên đĩa (24/4) đã chết → **user phải đăng nhập lại** để verify live (không tự test được autonomous).
- **Models hợp lệ của account** (từ `~/.codex/models_cache.json`): `gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex, gpt-5.2`. → `DEFAULT_MODEL="gpt-5.5"`.
- **redirect_uri cổng 1455:** dựng listener tạm (`codex_login_server.py`) bắt callback, đóng sạch sau khi xong.

### ĐÃ VERIFY LIVE (2026-06-13, token thật sau khi user login):
- ✅ **Generate** qua `codex/responses` chạy OK — trả PNG ~700KB.
- ✅ **Edit qua `input_image`** chạy OK — trả ảnh khác gốc. **KHÔNG cần fallback API key.**
- 2 bug phát hiện + fix khi chạy thật:
  1. Body THIẾU field `instructions` → 400 "Instructions are required". Fix: thêm `instructions` (system prompt) vào body.
  2. Header `version="0.47.0"` (lấy nhầm từ `codex --version`) quá thấp → 400 "gpt-5.5 requires a newer version of Codex". Fix: `version="0.124.0"` (= `client_version` trong `models_cache.json` — version Codex thật dùng truy cập gpt-5.5).
- Login fail trước đó chỉ do backend chưa restart (route 404) — không phải bug code.

### Lưu ý vận hành:
- Đổi code backend phải restart uvicorn (hoặc dùng `--reload`).
- `version` header bám theo `client_version` trong models_cache; OpenAI nâng version gate model mới → có thể cần cập nhật lại nếu model tương lai bị 400.
