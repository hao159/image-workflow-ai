---
title: 'Đại tu giao diện: phong cách trung tính + theme sáng/tối system'
description: >-
  Bỏ tông tím/glow kiểu AI; chuyển sang phong cách trung tính chuyên nghiệp
  (slate + accent xanh dương dịu), bổ sung theme Sáng/Tối/System với nút chuyển
  tay.
status: completed
priority: P2
branch: main
tags:
  - frontend
  - ui
  - theming
  - redesign
blockedBy: []
blocks: []
created: '2026-06-14T14:12:53.909Z'
createdBy: 'ck:plan'
source: skill
---

# Đại tu giao diện: phong cách trung tính + theme sáng/tối system

## Overview

Frontend hiện dark-only, tông **tím #7c5cff + glow/scan/sparkles** mang "hơi hướng AI".
Mục tiêu: **phong cách trung tính chuyên nghiệp** (nền slate, accent xanh dương dịu
`#3b6cf0`, phẳng, bóng nhẹ — kiểu SaaS) + **theme Sáng/Tối/System** chọn được trong
Cài đặt (lưu localStorage). Phạm vi: **đại tu toàn diện** — token, layout, spacing,
typography, radius, component, và loại bỏ tín hiệu AI (sparkles icon, glow neon).

Kiến trúc thuận lợi: gần như mọi màu đã đi qua CSS custom properties trong `:root`
(`frontend/src/styles.css:10-58`). Việc chính là **tách token thành bộ Sáng + Tối**,
**tokenize các màu hardcode còn sót** (~20 chỗ), và **đại tu thị giác** trên nền token đó.

## Quyết định người dùng (locked)

- **Phong cách:** Trung tính chuyên nghiệp — slate + accent `#3b6cf0`, phẳng, không glow neon.
- **Theme:** System + nút chuyển tay (Hệ thống / Sáng / Tối) trong Cài đặt, nhớ localStorage.
- **Phạm vi:** Đại tu toàn diện (màu + layout/spacing/typography/radius + bỏ tín hiệu AI).

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Token & theme foundation](./phase-01-token-theme-foundation.md) | Completed |
| 2 | [Theme switcher (System/Sáng/Tối)](./phase-02-theme-switcher-system-s-ng-t-i.md) | Completed |
| 3 | [Component restyle (toolbar/palette/node/modal)](./phase-03-component-restyle-toolbar-palette-node-modal.md) | Completed |
| 4 | [Loại tín hiệu AI & React Flow theming](./phase-04-lo-i-t-n-hi-u-ai-react-flow-theming.md) | Completed |
| 5 | [QA & tài liệu](./phase-05-qa-t-i-li-u.md) | Completed |

## Thứ tự thực thi

Tuần tự: 1 → 2 → 3 → 4 → 5. Phase 1 đặt nền token (mọi phase sau phụ thuộc). Phase 2
thêm cơ chế switch. Phase 3-4 đại tu thị giác + bỏ tín hiệu AI. Phase 5 QA + docs.

## Dependencies

- Không phụ thuộc plan khác. Đã quét `plans/` — các plan trước (codex-oauth, harness,
  model-dropdown...) không chạm CSS/theme → không có `blockedBy`/`blocks`.
- Toàn bộ thay đổi nằm trong `frontend/src/` (CSS + 4-5 file JS/JSX). Backend không đổi.
