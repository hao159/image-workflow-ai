---
title: Hybrid model dropdown for providers
description: >-
  Đổi ô Model free-text trong ⚙ Cài đặt thành dropdown hybrid: list curated tĩnh
  hiện ngay + nút "⟳ Tải từ API" fetch danh sách model live theo provider
  (gemini/openai/comfyui) + option "✎ Nhập tay". Áp dụng mọi provider hiện có.
status: completed
priority: P2
branch: main
tags:
  - providers
  - frontend
  - settings
  - dx
blockedBy: []
blocks: []
created: '2026-06-14T10:19:10.197Z'
createdBy: 'ck:plan'
source: skill
---

# Hybrid model dropdown for providers

## Overview

Thay ô Model nhập-tay (`SettingsModal.jsx:202`) bằng dropdown hybrid để người dùng
chọn model thay vì nhớ/gõ tên. **Không động đến auth** (đã bỏ Gemini OAuth khỏi scope).

Hybrid = 3 nguồn trong 1 control:
1. **List tĩnh curated** theo provider — hiện ngay, không cần mạng/key.
2. **"⟳ Tải từ API"** — fetch live danh sách model thật (gemini ListModels, openai
   `/v1/models`, comfyui checkpoints). Fail mềm → giữ list tĩnh + báo lỗi inline.
3. **"✎ Nhập tay"** — escape hatch, gõ tên model tự do (giữ hành vi cũ).

**Insight:** `model_configs.model` vẫn là string tự do trong DB — dropdown chỉ là lớp
UX chọn giá trị, không đổi schema, không đổi cách node resolve config.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Model catalog API](./phase-01-model-catalog-api.md) | Completed |
| 2 | [Frontend hybrid dropdown](./phase-02-frontend-hybrid-dropdown.md) | Completed |
| 3 | [Tests and docs](./phase-03-tests-and-docs.md) | Completed |

## Dependencies

- Phase 2 phụ thuộc Phase 1 (UI gọi endpoint).
- Phase 3 sau cùng.
- Cross-plan: không.

## Key Constraints

- File code < 200 LOC; tách `model_catalog.py` (backend) + `model-field.jsx` (frontend) nếu cần.
- Fetch live luôn fail mềm — static list là nguồn chính, live là bổ sung.
- Không đổi schema DB; không đổi resolve_model_config / cách node chọn config.
- Không gửi API key qua URL (dùng POST body cho fetch-live).
- YAGNI: không cache live list phía server; fetch theo yêu cầu nút bấm.
