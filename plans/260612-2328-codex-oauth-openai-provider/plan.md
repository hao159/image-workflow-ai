---
title: Đăng nhập OpenAI qua Codex OAuth + dọn config/model UI
description: >-
  Thêm provider codex (OAuth ChatGPT → Responses API tạo/sửa ảnh), xóa 3
  provider thô khỏi dropdown node, bỏ ô nhập model trong node.
status: completed
priority: P2
branch: ''
tags:
  - oauth
  - openai
  - codex
  - provider
  - ui
blockedBy: []
blocks: []
created: '2026-06-12T16:29:59.888Z'
createdBy: 'ck:plan'
source: skill
---

# Đăng nhập OpenAI qua Codex OAuth + dọn config/model UI

## Overview

3 mục tiêu user:
1. **Đăng nhập OpenAI qua OAuth Codex** ("Sign in with ChatGPT") → dùng model OpenAI (tạo/sửa ảnh) qua subscription, không cần API key.
2. **Xóa 3 config provider mặc định** (gemini/openai/comfyui thô) khỏi dropdown node.
3. **Bỏ ô nhập "Model"** trong node Tạo/Sửa ảnh — model lấy từ config.

Cốt lõi kỹ thuật: token OAuth **không** gọi được `api.openai.com` SDK cũ → phải gọi `chatgpt.com/backend-api/codex/responses` (Responses API + SSE), tool `image_generation` trả base64 PNG. → **Provider mới `codex`** chạy đường này; provider `openai` (API key) giữ nguyên fallback.

Research: `plans/reports/research-260612-2316-codex-oauth-openai-image-integration-report.md` (§3-8 + §11 quyết định đã chốt).

## Quyết định đã chốt (user 2026-06-12)
- Login: **cả hai** — đọc `~/.codex/auth.json` nếu có; thiếu thì chạy full OAuth flow (PKCE, callback cổng 1455).
- Edit ảnh: **thử `input_image`** trong Responses API; fail thì tính sau.
- Dropdown rỗng (chưa có config): **báo "Mở ⚙ Cài đặt model"** (không auto-seed, không fallback ẩn).
- ToS: **OK** — tool local cá nhân, không host/share token.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Config & Node Cleanup](./phase-01-config-node-cleanup.md) | Completed |
| 2 | [OAuth Core Module](./phase-02-oauth-core-module.md) | Completed |
| 3 | [Codex Image Provider](./phase-03-codex-image-provider.md) | Completed |
| 4 | [Backend OAuth Endpoints](./phase-04-backend-oauth-endpoints.md) | Completed |
| 5 | [Frontend Login UI](./phase-05-frontend-login-ui.md) | Completed |
| 6 | [Testing & Verification](./phase-06-testing-verification.md) | Completed |

## Dependencies

- Phase 1: độc lập (làm trước, nhanh, ít rủi ro).
- Phase 2 (OAuth core): nền tảng cho Phase 3 & 4.
- Phase 3 (provider codex) ← Phase 2.
- Phase 4 (endpoints) ← Phase 2.
- Phase 5 (frontend) ← Phase 1 + Phase 4.
- Phase 6: sau cùng.

Thứ tự thực thi: 1 → 2 → (3 ∥ 4) → 5 → 6.

## Key Risks
- Edit qua `input_image` chưa verify (cần token thật) → Phase 3 + 6.
- Header Responses API (`originator`/`session_id`/`version`/`OpenAI-Beta`) có thể đổi theo Codex CLI → dùng giá trị từ research, verify lúc test.
- Task 2 gây crash frontend nếu `spec.options` undefined (`WorkflowNode.jsx:24`) → Phase 1 phải guard.

## Cross-plan
Không có plan nào trùng lặp (scan `./plans/` 2026-06-12).
