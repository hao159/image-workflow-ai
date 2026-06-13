---
title: Prompt bổ sung + đại tu node Ghép prompt
description: >-
  Node text-input (Enhance/Tạo ảnh/Sửa ảnh): khi cổng prompt đã nối, ô prompt
  trong node đổi thành "Prompt bổ sung" + ghép vào prompt nối (hết cảnh gõ vô vô
  tác dụng). Node Ghép prompt: nhận nhiều dây, bỏ separator, nối bằng xuống
  dòng.
status: completed
priority: P2
branch: ''
tags:
  - nodes
  - ui
  - prompt
  - react-flow
blockedBy: []
blocks: []
created: '2026-06-13T04:16:38.096Z'
createdBy: 'ck:plan'
source: skill
---

# Prompt bổ sung + đại tu node Ghép prompt

## Overview

Sửa UX node-based image tool. Hai tính năng độc lập:

- **A — "Prompt bổ sung":** 3 node AI (`enhance_prompt`, `generate_image`, `edit_image`) hiện dùng `inputs.get(x) or params.get(y)` → nối dây thì ô prompt soạn-tay bị bỏ qua âm thầm. Đổi sang **ghép** (`nối_vào, bổ_sung`) qua helper dùng chung; UI relabel ô + badge "✓ đã nối" khi cổng đang nối.
- **B — Đại tu `combine_text`:** từ 2 cổng cố định `a`/`b` + param separator → 1 cổng `texts` (multiple), bỏ separator, nối bằng `\n`. Có shim tương thích workflow cũ.

Nguồn: design doc đã duyệt → `plans/reports/from-brainstorm-to-planner-260613-1100-prompt-supplement-combine-report.md`.

Nguyên tắc: YAGNI/KISS/DRY. Engine (`engine.py`) đã hỗ trợ cổng `multiple` → **không đổi engine**. UI tự sinh từ metadata → đổi metadata `Param` là đủ, không hard-code từng node ở frontend.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Backend prompt bổ sung (metadata + helper + node AI)](./phase-01-backend-prompt-b-sung-metadata-helper-node-ai.md) | Completed |
| 2 | [Backend đại tu Ghép prompt (multi-input + shim)](./phase-02-backend-i-tu-gh-p-prompt-multi-input-shim.md) | Completed |
| 3 | [Frontend badge và relabel cổng đã nối](./phase-03-frontend-badge-v-relabel-c-ng-n-i.md) | Completed |
| 4 | [Tests và verify](./phase-04-tests-v-verify.md) | Completed |

## Dependencies

- Phase 3 (frontend) **blockedBy** Phase 1 — cần field `supplement_for`/`supplement_label` xuất trong metadata.
- Phase 4 (tests) **blockedBy** Phase 1, 2, 3.
- Phase 1 và Phase 2 độc lập (node khác nhau, không chung helper) — chạy tuần tự hoặc song song đều được.
- Cross-plan: không. (Plan codex-oauth đã `completed`, chỉ chạm `providers/`.)
