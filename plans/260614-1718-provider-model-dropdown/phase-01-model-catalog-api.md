---
phase: 1
title: Model catalog API
status: completed
priority: P1
effort: 0.5d
dependencies: []
---

# Phase 1: Model catalog API

## Overview

Backend cho dropdown: catalog tĩnh curated theo provider + endpoint fetch live danh
sách model. Kết thúc phase: `POST /api/providers/{provider}/models` trả `{static, live, error}`.

## Requirements

- Functional:
  - List tĩnh curated mỗi provider (luôn có, không gọi mạng/key).
  - Fetch live tùy chọn theo provider khi có key/base_url; lỗi → trả static + `error`, HTTP 200.
- Non-functional: fetch live có timeout; fail mềm; không nhận api_key qua URL (POST body).

## Architecture

**Catalog tĩnh** (`model_catalog.py` — dict):
| Provider | Static |
|---|---|
| gemini | `gemini-2.5-flash-image`, `gemini-2.5-flash`, `gemini-2.5-pro` |
| openai | `gpt-image-1`, `gpt-4o`, `gpt-4o-mini` |
| codex | `gpt-5.5` |
| comfyui | `[]` (chỉ live từ server) |

**Fetch live** (`fetch_live(provider, api_key, base_url) -> list[str]`):
| Provider | Nguồn |
|---|---|
| gemini | SDK `genai.Client(api_key).models.list()` → tên model |
| openai | `GET {base_url or https://api.openai.com}/v1/models` Bearer api_key |
| comfyui | `GET {base_url}/object_info/CheckpointLoaderSimple` → list checkpoint |
| codex | trả `[]` (không list được; chỉ static) |

**Endpoint** (`main.py`): `POST /api/providers/{provider}/models`, body JSON
`{ "config_id"?: int, "api_key"?: str, "base_url"?: str }`.
- Resolve key/base_url: `config_id` có → load từ DB (key đã lưu); else dùng `api_key`/`base_url` body.
- Trả `{ "static": [...], "live": [...], "error": str|null }`. `fetch_live` raise → bắt → `error` set, `live: []`.
- Provider không hợp lệ → 400.

**Lý do POST + config_id:** lúc tạo config mới key gõ trong form (chưa lưu) → gửi `api_key`;
lúc sửa config key form để trống (giữ key cũ) → gửi `config_id` để backend dùng key đã lưu.

## Related Code Files

- Create: `backend/app/providers/model_catalog.py`
- Modify: `backend/app/main.py` (route mới)
- Modify: `backend/app/db.py` (thêm `get_model_config_by_id(id)` — hiện chỉ có theo name)
- Read for context: `backend/app/providers/gemini.py`, `openai_provider.py`, `comfyui.py`

## Implementation Steps

1. `model_catalog.py`: `STATIC: dict[str, list[str]]` + `fetch_live(provider, api_key, base_url)`
   (try mỗi provider, parse phòng thủ; lỗi → raise để caller bắt). Lọc tên model gemini gọn nếu cần.
2. `db.py`: `get_model_config_by_id(config_id) -> dict | None` (SELECT theo id).
3. `main.py`: route `POST /api/providers/{provider}/models`:
   - validate provider ∈ catalog (else 400).
   - resolve key/base_url (config_id > body).
   - `static = STATIC[provider]`; try `live = fetch_live(...)` except → `error`.
   - trả JSON.

## Success Criteria

- [ ] `POST /api/providers/gemini/models` body rỗng → trả static, `live: []`, `error: null`.
- [ ] Body có `api_key` hợp lệ → trả `live` (gemini/openai); comfyui có `base_url` → checkpoints.
- [ ] Key sai / server offline → `error` set, `static` vẫn trả, HTTP 200 (không 500).
- [ ] `model_catalog.py` < 200 LOC; không log api_key.

## Risk Assessment

- **API list đổi shape** → parse phòng thủ, fail mềm về static.
- **comfyui offline / openai timeout** → bắt lỗi kết nối, `error` mềm.
