---
phase: 5
title: QA & tài liệu
status: completed
priority: P2
effort: 2-3h
dependencies:
  - 1
  - 2
  - 3
  - 4
---

# Phase 5: QA & tài liệu

## Overview

Rà soát chất lượng cuối: tương phản/đọc được ở cả 2 theme, không sót màu kẹt, không
regress hành vi; tinh chỉnh token cho đẹp; cập nhật tài liệu (`docs/`, README nếu cần).

## Requirements

- Functional: toàn bộ luồng chính hoạt động ở cả Sáng & Tối (kéo thả, nối dây, chạy,
  harness, cài đặt, viewer, lưu/mở workflow).
- Non-functional: tương phản đạt mức đọc tốt (mục tiêu WCAG AA cho text chính); không
  nhấp nháy; reduced-motion ổn.

## Key Insights

- Phần lớn lỗi sẽ là **tương phản light mode** (chữ dim trên trắng) và **vài màu sót**
  chưa tokenize → grep + soi mắt là đủ; không cần test tự động nặng.
- Dự án không có test frontend sẵn → QA chủ yếu thủ công + (tùy chọn) chụp ảnh so sánh.

## Checklist QA (cả 2 theme)

- [ ] Toolbar: nút, status chip (ok/err/busy), menu workflow, harness popover.
- [ ] Palette: brand, search, item, hover, kéo thả vào canvas.
- [ ] Node: header, ports/handles, param fields (text/number/select/textarea/checkbox),
      upload, preview ảnh, file card, text output, error box.
- [ ] Trạng thái node: idle/running(solid)/done/error + badge cache + badge "đã nối".
- [ ] Canvas: grid, edges (thường/hover/selected/animated), connection line, controls, minimap.
- [ ] Modal Cài đặt: section Giao diện (theme switch + hiệu ứng), bảng model, form,
      oauth box, model field.
- [ ] Connect menu (kéo dây thả ra trống) + Image viewer modal.
- [ ] Theme switch: System/Sáng/Tối; đổi OS realtime; nhớ qua reload; không FOUC.
- [ ] reduced-motion: tắt animation OS → không hiệu ứng động.
- [ ] Tương phản: chữ chính, chữ dim, placeholder, viền trên cả 2 nền.

## Related Code Files

- Modify (tinh chỉnh): `frontend/src/styles.css` + các `styles/*.css` — chỉnh token màu/
  tương phản theo phát hiện QA.
- Modify (docs): `docs/` — cập nhật `system-architecture.md` / `codebase-summary.md` /
  `code-standards.md` phần frontend theming nếu các file này có tồn tại & liên quan;
  `docs/project-changelog.md` thêm mục redesign (nếu file tồn tại — kiểm trước).
- Modify (tùy chọn): `README.md` — nếu cần ghi chú theme switch trong mục giao diện.

## Implementation Steps

1. Grep lại `frontend/src/**/*.css` cho hex/rgba hardcode (lưới chặn Phase 1) — fix nốt.
2. Chạy `npm run dev`, đi hết checklist QA ở **cả Sáng & Tối**.
3. Tinh chỉnh token tương phản các chỗ chưa đạt.
4. (Tùy chọn) `/ck:code-review` cho diff frontend; sửa theo khuyến nghị.
5. Cập nhật tài liệu liên quan trong `docs/` (kiểm file tồn tại trước khi sửa) + README
   nếu cần. Thêm changelog.
6. Build thử (`npm run build --prefix frontend`) để chắc không lỗi production.

## Todo List

- [ ] Grep chặn màu hardcode còn sót → fix
- [ ] Đi hết checklist QA (Sáng + Tối)
- [ ] Tinh chỉnh tương phản token
- [ ] (Tùy chọn) code-review diff + sửa
- [ ] Cập nhật docs/ + README + changelog (file nào tồn tại)
- [ ] `npm run build` pass

## Success Criteria

- [ ] Toàn bộ checklist QA pass ở cả 2 theme.
- [ ] Không còn màu hardcode phá theme (grep sạch).
- [ ] `npm run build` thành công, không lỗi/cảnh báo nghiêm trọng.
- [ ] Tài liệu phản ánh tính năng theme + phong cách mới.

## Risk Assessment

- **Thiếu test tự động** → dựa QA thủ công; bù bằng checklist đầy đủ + build check.
- **Tương phản biên** (AA) khó đạt với màu quá dịu → ưu tiên đọc được hơn là "đẹp dịu";
  nâng `--text-dim` nếu cần.
- **Docs lệch thực tế:** chỉ sửa file docs đang tồn tại & liên quan (kiểm bằng glob trước),
  tránh tạo tài liệu thừa (YAGNI).
