---
phase: 6
title: Testing & Verification
status: completed
priority: P2
effort: 2h
dependencies:
  - 1
  - 3
  - 5
---

# Phase 6: Testing & Verification

## Overview
Verify toàn bộ luồng end-to-end với token thật: cleanup UI (Phase 1), login OAuth (Phase 4/5), tạo ảnh qua codex (Phase 3), và xác nhận edit qua input_image (điểm chưa chắc chắn từ research §5.1).

## Requirements
- Functional: backend chạy không lỗi; node UI đúng; login ghi token; generate ra ảnh; edit chạy hoặc báo lỗi rõ.
- Non-functional: không hardcode token vào test; không commit token; test e2e cần backend chạy (như `backend/test_e2e.py` hiện có).

## Architecture
2 lớp test:
- **Unit/mạng-độc-lập** (không cần token): PKCE generate, build_authorize_url format, ASPECT→size map, SSE parser với fixture event giả (feed chuỗi `data:` mẫu → ra bytes), make_provider("codex") tạo được, provider_options không còn provider thô.
- **Manual/e2e** (cần `~/.codex/auth.json` thật — user đã `codex login` hoặc login qua app): status, generate ảnh thật, edit ảnh thật.

## Related Code Files
- Create/Modify: `backend/test_e2e.py` hoặc thêm test riêng `backend/test_codex.py` — unit cho oauth core + SSE parser (fixture).
- Reference: tất cả file các phase trước.

## Implementation Steps
1. **Unit (delegate tester):**
   - `generate_pkce()` → verifier/challenge hợp lệ (challenge = base64url sha256).
   - `build_authorize_url()` chứa đủ params bắt buộc.
   - SSE parser: feed fixture chuỗi event (`response.image_generation_call.in_progress`, `...generating`, `response.output_item.done` với item.result base64 PNG 1x1) → trả đúng bytes.
   - `provider_options()` không chứa "gemini"/"openai"/"comfyui" thô.
   - `make_provider("codex")` không raise.
   - node metadata generate/edit KHÔNG còn param "model".
2. **Backend smoke:** chạy backend, `GET /api/node-types` (param provider không có options thô, không có param model), `GET /api/oauth/openai/status`.
3. **Frontend smoke:** dev server, mở canvas + ⚙ Model, không lỗi console; node hiện hint khi 0 config.
4. **Manual OAuth (cần user):** bấm Đăng nhập → login ChatGPT → status logged_in; HOẶC dùng `codex login` sẵn có.
5. **Manual generate:** tạo config codex → node Tạo ảnh → ▶ Chạy → ra ảnh. Ghi lại model field nào hoạt động.
6. **Manual edit (verify §5.1):** node Sửa ảnh + config codex → chạy. Ghi kết quả: (a) edit OK qua input_image → giữ; (b) fail → xác nhận ProviderError message hiển thị đúng, quyết định fallback (báo user / tắt codex cho node edit).
7. Fix lỗi phát sinh, chạy lại tới khi pass. KHÔNG dùng mock để "qua" test thật.

## Todo List
- [ ] Unit: PKCE, authorize URL, SSE parser fixture
- [ ] Unit: provider_options sạch, make_provider codex, node metadata không có model
- [ ] Backend smoke (node-types, oauth status)
- [ ] Frontend smoke (canvas, modal, hint 0 config)
- [ ] Manual: login OAuth ghi token
- [ ] Manual: generate ra ảnh (xác định model hợp lệ)
- [ ] Manual: edit — xác nhận OK hoặc fallback
- [ ] Cập nhật research report §11 với kết quả verify edit + model

## Success Criteria
- [ ] Tất cả unit test pass.
- [ ] Backend + frontend chạy không lỗi với các thay đổi Phase 1.
- [ ] Login OAuth thành công, token ghi `~/.codex/auth.json`.
- [ ] Generate ảnh qua codex trả ảnh thật.
- [ ] Edit: kết quả rõ ràng (OK hoặc lỗi có message hữu ích) — không crash engine.
- [ ] Không token/secret nào bị commit.

## Risk Assessment
- **Edit fail** là kịch bản dự kiến có thể xảy ra → đã có nhánh fallback message (Phase 3 bước 6). Nếu fail và user cần edit → mở mini-quyết định: node Sửa ảnh dùng provider OpenAI API key.
- **Model field sai** → thử vài giá trị (gpt-5.5/gpt-5.3-codex...) hoặc gọi `/backend-api/models`; cập nhật DEFAULT_MODEL.
- **Test e2e cần backend chạy** → tài liệu hóa bước chạy backend trước (đã có trong README).

## Next Steps
- Sau khi pass: `docs-manager` cập nhật README (provider codex, cách login) + `docs/` nếu có.
- `code-reviewer` review toàn bộ thay đổi.
