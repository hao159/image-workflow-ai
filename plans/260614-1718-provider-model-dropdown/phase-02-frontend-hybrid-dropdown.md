---
phase: 2
title: Frontend hybrid dropdown
status: completed
priority: P1
effort: 0.5d
dependencies:
  - 1
---

# Phase 2: Frontend hybrid dropdown

## Overview

Thay ô Model free-text trong SettingsModal bằng component dropdown hybrid: select
list (static + live) + nút tải-từ-API + option "Nhập tay".

## Requirements

- Functional:
  - Đổi provider → load static list ngay (gọi endpoint với body rỗng hoặc dùng static client-side).
  - Nút "⟳ Tải từ API" → POST endpoint (kèm api_key form hoặc config_id khi sửa) → merge `live` vào options.
  - Option "✎ Nhập tay" → hiện `<input>` text như cũ; giữ value khi switch qua lại.
- Non-functional: static render ngay; fetch live non-blocking (spinner ở nút); lỗi hiện inline, không vỡ form.

## Architecture

**api.js thêm:** `listProviderModels(provider, { configId, apiKey, baseUrl })`
→ `POST /api/providers/{provider}/models`. Trả `{static, live, error}` (xử lỗi như các hàm hiện có).

**Component `model-field.jsx`** (tách riêng cho gọn, SettingsModal đang ~227 LOC):
- Props: `provider`, `configId`, `apiKey`, `baseUrl`, `value`, `onChange`.
- State: `options` (static∪live), `loading`, `error`, `manual` (bool).
- Sentinel `__manual__` trong `<select>`; chọn → `manual=true` → render `<input>`.
- Khi `provider` đổi → reset options về static (gọi endpoint body rỗng, hoặc static map client).
- Nút refresh → `listProviderModels` với key/config hiện tại → merge `live`, dedupe.
- **Prefill khi sửa config:** nếu `value` ∈ options → select; nếu không (model lạ) → `manual=true`, input điền sẵn `value` (không mất dữ liệu cũ).

**SettingsModal.jsx:** thay block `<label><span>Model</span><input.../></label>`
(dòng 202-210) bằng `<ModelField .../>` truyền `form.provider/id/api_key/base_url/model`
và `onChange={(v) => set('model', v)}`.

## Related Code Files

- Modify: `frontend/src/api.js` (hàm `listProviderModels`)
- Create: `frontend/src/components/model-field.jsx`
- Modify: `frontend/src/components/SettingsModal.jsx` (thay ô Model)
- Modify (nếu cần): `frontend/src/styles/settings-modal.css` (style select + nút refresh + spinner)

## Implementation Steps

1. `api.js`: thêm `listProviderModels(provider, opts)` (POST, body từ opts; bỏ field rỗng).
2. `model-field.jsx`: dựng select hybrid + sentinel "Nhập tay" + nút refresh + state loading/error.
   Effect theo `provider` để nạp static. Prefill manual khi value lạ.
3. `SettingsModal.jsx`: import + thay ô Model bằng `<ModelField>`. Bỏ `providerMeta?.defaultModel`
   placeholder cũ hoặc chuyển vào component (hiển thị "mặc định = …" trong option trống).
4. CSS nhỏ cho layout select+nút.

## Success Criteria

- [ ] Ô Model là dropdown: chọn provider → hiện static list ngay.
- [ ] "⟳ Tải từ API" với key hợp lệ → thêm model live vào list; lỗi → báo inline, list tĩnh còn nguyên.
- [ ] "✎ Nhập tay" → gõ tên tự do; lưu config giữ đúng giá trị.
- [ ] Sửa config có model lạ → rơi vào "Nhập tay" với value điền sẵn.
- [ ] `model-field.jsx` < 200 LOC; build pass.

## Risk Assessment

- **State manual vs list rối** → sentinel `__manual__` rõ ràng; 1 nguồn sự thật là `value` (prop).
- **Fetch live chậm** → spinner trên nút, không chặn render/lưu.
