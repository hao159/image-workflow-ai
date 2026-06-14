---
phase: 3
title: Component restyle (toolbar/palette/node/modal)
status: completed
priority: P2
effort: 6-8h
dependencies:
  - 1
  - 2
---

# Phase 3: Component restyle (toolbar/palette/node/modal)

## Overview

Đại tu thị giác trên nền token mới: cập nhật **typography, spacing, radius, độ dày viền,
bóng** để ra phong cách trung tính chuyên nghiệp (phẳng, gọn, ít trang trí). Áp đồng nhất
cho toolbar, palette (sidebar), node trên canvas, modal cài đặt, menu, image viewer.

## Requirements

- Functional: mọi component giữ nguyên hành vi; chỉ đổi diện mạo.
- Non-functional: hệ thống thị giác nhất quán (1 thang spacing, 1 bộ radius, 1 thang chữ);
  đẹp ở cả 2 theme; tôn trọng `prefers-reduced-motion` (đã có).

## Key Insights

- Radius hiện hơi lớn/bo tròn (`--radius-lg: 14px`) tạo cảm giác "mềm AI" → hệ trung tính
  thường radius vừa (8-10px). Đổi token radius lan toàn app, ít rủi ro.
- Font đang `Inter` — phù hợp phong cách trung tính, giữ. Có thể siết `letter-spacing`
  và chuẩn hóa cỡ chữ theo thang.
- Phần lớn restyle = đổi **giá trị token** (radius, shadow, spacing biến nếu thêm) +
  vài tinh chỉnh per-component. Tránh viết lại CSS từ đầu (DRY).

## Architecture — hệ thị giác trung tính

- **Radius:** `--radius-sm: 6px`, `--radius-md: 8px`, `--radius-lg: 10px` (giảm từ 7/10/14).
- **Shadow:** nhẹ hơn, ít "đổ bóng tím" — đã đặt ở Phase 1; ở light dùng bóng xanh-xám rất nhạt.
- **Spacing:** thêm token `--space-1..-4` (4/8/12/16px) tùy chọn để chuẩn hóa padding;
  hoặc giữ giá trị px hiện tại nếu đã đều — quyết khi thực thi (YAGNI).
- **Viền:** giảm độ dày node từ `1.5px` xuống `1px` (trừ trạng thái selected/running) cho phẳng.
- **Buttons:** primary phẳng (accent đặc, bỏ glow box-shadow tím L106-110 → bóng nhẹ trung tính);
  ghost/secondary giữ.
- **Header node:** bỏ "strip accent + glow"? — KHÔNG bỏ hẳn ở phase này (thuộc Phase 4
  "tín hiệu AI"); ở đây chỉ chuẩn hóa padding/typography. Ranh giới: **Phase 3 = hình khối/chữ/
  khoảng cách; Phase 4 = bỏ hiệu ứng động + sparkles**.

## Related Code Files

- Modify: `frontend/src/styles.css` — token radius/spacing; nút primary bỏ glow tím
  (L100-111) → bóng trung tính; chuẩn typography (`--font` giữ).
- Modify: `frontend/src/styles/toolbar.css` — padding/cao toolbar, status chip bo & cỡ,
  wf-name input.
- Modify: `frontend/src/styles/palette.css` — brand/logo, search, palette-item spacing &
  radius, hover (bỏ `translateX(2px)`? giữ nhẹ — quyết khi QA).
- Modify: `frontend/src/styles/workflow-node.css` — radius node, độ dày viền, header
  padding, ports, param fields, file/preview cards.
- Modify: `frontend/src/styles/settings-modal.css` — modal radius, section spacing,
  table, form (đọc file này khi thực thi — chưa đọc ở research).
- Modify: `frontend/src/styles/connect-menu.css`, `image-viewer-modal.css` — đồng bộ
  radius/shadow/scrim (đọc khi thực thi).
- Modify (tùy chọn nhỏ): `frontend/src/components/Palette.jsx` — chỉ nếu cần đổi text
  brand/subtitle cho bớt "AI" (vd subtitle). Không bắt buộc.

## Implementation Steps

1. Đọc các CSS chưa xem ở research: `settings-modal.css`, `connect-menu.css`,
   `image-viewer-modal.css` (bắt buộc trước khi sửa — Read-before-Edit).
2. Giảm token radius (sm/md/lg) trong `styles.css`; verify toàn app không bị "vuông gắt".
3. Nút primary: bỏ box-shadow glow tím, dùng bóng trung tính + hover đổi nền nhẹ.
4. Toolbar: chuẩn hóa chiều cao, padding, status chip (bo + cỡ chữ), separator.
5. Palette: brand block, search input, item card (padding/radius/hover) theo hệ mới.
6. Node: viền 1px, header padding, ports, form fields, preview/file card — đồng nhất.
7. Modal/menu/viewer: radius + shadow + scrim đồng bộ token.
8. Soát 2 theme cho từng nhóm component (Sáng + Tối).

## Todo List

- [ ] Đọc 3 CSS còn lại (settings-modal, connect-menu, image-viewer-modal)
- [ ] Giảm radius token + bỏ glow tím nút primary
- [ ] Restyle toolbar (chiều cao/padding/chip/input)
- [ ] Restyle palette (brand/search/item)
- [ ] Restyle node (viền/header/ports/form/cards)
- [ ] Restyle modal/menu/viewer (radius/shadow/scrim)
- [ ] Soát từng nhóm ở cả Sáng & Tối

## Success Criteria

- [ ] Toàn app dùng radius/shadow/spacing nhất quán theo token mới ở cả 2 theme.
- [ ] Không còn bóng/đổ glow tông tím ở các component thường (nút, chip, card).
- [ ] Hành vi không đổi: kéo thả node, mở menu, modal, viewer vẫn chạy.
- [ ] Tương phản chữ/nền đạt mức đọc tốt ở cả Sáng & Tối (kiểm mắt; QA kỹ ở Phase 5).

## Risk Assessment

- **Phình phạm vi:** "đại tu toàn diện" dễ trôi → giữ ranh giới Phase 3 (hình/chữ/khoảng
  cách) vs Phase 4 (hiệu ứng/biểu tượng AI). Không tái cấu trúc DOM trừ khi cần.
- **Light mode nhạt nhòa:** viền 1px + bóng nhẹ trên nền trắng dễ "mất nét" → đảm bảo
  `--border` light đủ tương phản (≥ #e2e5ea) + dùng `--bg-panel` trắng tách nền `--bg-app` xám.
- **Regress hành vi do sửa nhầm selector** → chỉ sửa thuộc tính thị giác, không đổi
  layout flex/grid trừ khi có chủ đích.
