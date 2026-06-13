---
phase: 3
title: Codex Image Provider
status: completed
priority: P1
effort: 4h
dependencies:
  - 2
---

# Phase 3: Codex Image Provider

## Overview
Provider mới `codex` kế thừa `ImageProvider`: tạo ảnh (và thử sửa ảnh) qua `chatgpt.com/backend-api/codex/responses` bằng token OAuth từ Phase 2. Parse SSE stream lấy base64 PNG. Đăng ký vào `PROVIDER_CLASSES`.

## Requirements
- Functional: `generate(prompt, model, aspect_ratio)` trả PNG bytes; `edit(images, prompt, model)` thử qua `input_image`; tự lấy/refresh token qua OAuth core.
- Non-functional: dưới 200 dòng (tách SSE parser ra helper nếu cần); lỗi rõ ràng; không lưu token trong provider lâu dài (lấy lúc gọi).

## Architecture
Request (research §4):
```
POST https://chatgpt.com/backend-api/codex/responses
Headers:
  Authorization: Bearer <access_token>
  chatgpt-account-id: <account_id>
  OpenAI-Beta: responses=experimental
  originator: codex_cli_rs
  session_id: <uuid4 mỗi request>
  Content-Type: application/json
  Accept: text/event-stream
Body:
{
  "model": "<model coding, vd gpt-5.5>",   # tool tự chọn gpt-image nội bộ
  "tools": [{"type": "image_generation", "size": "<WxH>"}],
  "input": [{"role":"user","content":[{"type":"input_text","text": prompt}]}],
  "stream": true
}
```
- `aspect_ratio` → size: reuse map giống `openai_provider.ASPECT_TO_SIZE` (1:1→1024x1024, ...). Có thể import dùng chung (DRY) hoặc copy hằng nhỏ.
- **Model**: param `model` từ config = model dùng cho field `"model"` body. Default nếu trống: hằng `DEFAULT_MODEL` (vd `"gpt-5.5"` — verify model khả dụng cho account). Lưu ý: model ảnh thực tế do tool quyết; field model là model "host" coding.
- **SSE parse**: đọc stream line-by-line, gom `data: {...}` JSON; bắt event `response.output_item.done` có `item.type == "image_generation_call"` → `item.result` = base64 PNG → decode. Cũng nên xử lý `response.error` / item lỗi → raise ProviderError với message từ server.

`edit()`: thêm `{"type": "input_image", "image_url": "data:image/png;base64,<...>"}` (hoặc format Responses API đúng — **verify**) vào `content` cùng `input_text`, nhiều ảnh = nhiều input_image. Cùng tool image_generation. Nếu server từ chối (4xx/không trả image item) → `ProviderError("Codex OAuth chưa hỗ trợ sửa ảnh; dùng provider OpenAI API key.")`.

Token: gọi `openai_codex_oauth.get_valid_access_token()` đầu mỗi request. Nếu 401 → thử refresh 1 lần rồi retry (lazy refresh).

`resolve_model_config()` tương tác: config provider="codex" không có api_key. `make_provider("codex", ...)` tạo `OpenAICodexProvider()` (không cần api_key/base_url). Provider tự đọc token từ OAuth core, không nhận api_key.

## Related Code Files
- Create: `backend/app/providers/openai_codex.py` — class `OpenAICodexProvider(ImageProvider)`, name="codex".
- Create (nếu SSE parser lớn): `backend/app/providers/codex_sse.py` — helper `parse_image_from_sse(response) -> bytes`. Chỉ tách nếu file vượt ~180 dòng (YAGNI: ưu tiên 1 file).
- Modify: `backend/app/providers/__init__.py` — import `OpenAICodexProvider`, thêm `"codex": OpenAICodexProvider` vào `PROVIDER_CLASSES`; chỉnh `make_provider()` để nhánh codex không cần api_key (`if provider_name == "codex": return cls()`).
- Reference: `backend/app/providers/openai_provider.py` (ASPECT_TO_SIZE), `base.py` (interface), `openai_codex_oauth.py` (token).

## Implementation Steps
1. Tạo `openai_codex.py`: class skeleton, `name="codex"`, `__init__` không tham số bắt buộc.
2. Helper `_headers(access_token, account_id)` + `_size(aspect_ratio)`.
3. `_request_image(model, content_list)`: dựng body, httpx stream POST, parse SSE → bytes. Retry 1 lần khi 401 (refresh token).
4. SSE parser: iterate `response.iter_lines()`, tách `data: `, json.loads, dò `response.output_item.done` → image_generation_call → base64 decode. Raise nếu stream kết thúc không có ảnh.
5. `generate()`: content = `[{type:input_text, text:prompt}]` → `_request_image`.
6. `edit()`: content = input_text + input_image cho mỗi ảnh (base64 data URL) → `_request_image`; bắt lỗi server → ProviderError gợi ý dùng API key.
7. `__init__.py`: register codex + sửa make_provider nhánh codex.
8. Compile check: `python -c "from app.providers import make_provider; make_provider('codex')"` (không gọi mạng).

## Todo List
- [ ] openai_codex.py skeleton + headers/size helper
- [ ] _request_image + SSE parser (base64 PNG)
- [ ] 401 lazy-refresh retry
- [ ] generate()
- [ ] edit() qua input_image + fallback error message
- [ ] register "codex" trong PROVIDER_CLASSES + make_provider
- [ ] Compile check

## Success Criteria
- [ ] `make_provider("codex")` tạo được provider không cần api_key.
- [ ] (cần token thật) generate() trả PNG hợp lệ từ codex/responses.
- [ ] (cần token thật) edit() hoặc chạy được, hoặc báo lỗi rõ ràng (không crash engine).
- [ ] Lỗi server map sang ProviderError có message tiếng Việt dễ hiểu.

## Risk Assessment
- **Format `input_image` cho edit** chưa chắc → bước 6 bọc try/except, fallback message; verify Phase 6.
- **Model field giá trị đúng** (gpt-5.5 vs khác theo account) → DEFAULT_MODEL có thể cần chỉnh sau khi xem `/backend-api/models`; để dễ override qua config.model.
- **SSE format đổi** → parser nên log raw event khi không tìm thấy ảnh, để debug nhanh.
