---
phase: 1
title: Token & theme foundation
status: completed
priority: P1
effort: 4-6h
dependencies: []
---

# Phase 1: Token & theme foundation

## Overview

Đặt lại nền tảng màu: chuyển `:root` dark-only thành **2 bộ token Sáng + Tối** dựa trên
phong cách trung tính (slate + accent `#3b6cf0`), và **tokenize mọi màu hardcode còn sót**
để theme hoạt động đồng bộ. Đây là nền cho tất cả phase sau.

## Requirements

- Functional: app render đúng ở cả 2 theme; không còn màu cứng phá theme.
- Non-functional: giữ kiến trúc token tập trung; KISS — chỉ override token theo theme,
  không sửa rải rác từng selector.

## Key Insights

- Hầu hết màu đã ở `:root` (`frontend/src/styles.css:10-58`) → đổi 1 chỗ, lan toàn app.
- ~20 màu hardcode bypass token (xem danh sách bên dưới) → phải tokenize trước khi
  theme, nếu không các chỗ này sẽ "kẹt màu tối" khi sang nền sáng.
- Cơ chế theme dùng **attribute `[data-theme="light"|"dark"]` trên `<html>`** (Phase 2
  set), còn `:root` giữ giá trị mặc định = dark để không vỡ khi JS chưa chạy.

## Architecture — chiến lược token theo theme

```css
/* :root = bộ token mặc định (dark) — fallback khi chưa có data-theme */
:root, :root[data-theme="dark"] {
  --bg-app: ...; --text: ...; --accent: #3b6cf0; ...
}
:root[data-theme="light"] {
  --bg-app: #f7f8fa; --text: #1c1e26; --accent: #3b6cf0; ...
}
```

- Token **ngữ nghĩa** (semantic) giữ nguyên tên (`--bg-app`, `--text`, `--accent`,
  `--ok/err/run`, `--cat-*`, `--dtype-*`, `--shadow-*`) → component CSS không phải đổi tên.
- Mỗi theme định nghĩa lại **giá trị** của cùng tên token.
- Bảng màu trung tính đề xuất (tinh chỉnh khi QA, đây là điểm xuất phát):

| Token | Dark (mới) | Light (mới) |
|---|---|---|
| `--bg-app` | `#0f1115` | `#f5f6f8` |
| `--bg-canvas` | `#12141a` | `#eceef2` |
| `--bg-panel` | `#171a21` | `#ffffff` |
| `--bg-raised` | `#1e222b` | `#f5f6f8` |
| `--bg-input` | `#12141a` | `#ffffff` |
| `--bg-hover` | `#252a35` | `#e9ecf1` |
| `--border` | `#262b35` | `#e2e5ea` |
| `--border-strong` | `#363c49` | `#cdd2db` |
| `--text` | `#e7e9ef` | `#1c1e26` |
| `--text-dim` | `#9aa0b0` | `#5a6072` |
| `--text-faint` | `#6b7080` | `#8b91a1` |
| `--accent` | `#3b6cf0` | `#3257d6` |
| `--accent-hover` | `#5680ff` | `#2546bf` |
| `--accent-soft` | `rgba(59,108,240,0.18)` | `rgba(50,87,214,0.12)` |
| `--ok` | `#3ba776` | `#1f9d6b` |
| `--err` | `#e5575f` | `#d23b46` |
| `--run` | `#3b82d6` | `#2f6fc4` |
| `--shadow-md` | `0 8px 28px rgba(0,0,0,0.45)` | `0 6px 20px rgba(20,30,60,0.10)` |

- **Node categories** chuyển khỏi palette neon: `--cat-ai` BỎ tím (`#a78bfa`) → xanh dương
  trung `#5b8def`; `--cat-input` xanh lá dịu, `--cat-transform` hổ phách dịu, `--cat-output`
  lam dịu, `--cat-misc` xám. Giữ phân biệt nhưng giảm độ bão hòa (đỡ "neon AI").
- Thêm token mới cho overlay/badge để 2 theme khác nhau:
  - `--overlay-scrim` (nền mờ sau modal/icon-btn): dark `rgba(8,9,14,0.6)` / light `rgba(30,35,50,0.35)`.
  - `--badge-cache-bg/-fg`, `--badge-port-bg/-fg`, `--edge`, `--edge-hover` (cho React Flow, Phase 4 dùng).
  - `--warn` (đang dùng fallback rải rác trong toolbar.css) → định nghĩa chính thức.

## Related Code Files

- Modify: `frontend/src/styles.css` — tách `:root` thành 2 bộ theme + thêm token mới.
- Modify (tokenize màu hardcode):
  - `frontend/src/styles/workflow-node.css` — `#41435f` (L7) → `var(--border-strong)`;
    `#facc15` + `rgba(250,204,21,..)` (L120-121) → `var(--badge-cache-*)`;
    `#34d399` + `rgba(52,211,153,..)` (L142-143) → `var(--badge-port-*)`;
    glow rgba (L20,315-316) → dùng `--run` qua `color-mix` (hiệu ứng sẽ xử lý Phase 4).
  - `frontend/src/styles/toolbar.css` — status chip rgba (L56-67) → `color-mix(var(--ok/err/run))`;
    dọn fallback hardcode `#1b1c28/#e8e8f0/#e0a44a/#2a2b3a/#5fd17a` (L121-159) → bỏ fallback,
    dùng token (đã có `--warn`).
  - `frontend/src/styles/react-flow-overrides.css` — `#767b9e`/`#a0a4c4` (L5-6) → `var(--edge/--edge-hover)`;
    `rgba(16,17,23,0.72)` minimap-mask (L66) → `var(--overlay-scrim)` (Phase 4 hoàn thiện).
  - `frontend/src/styles.css` (buttons) — `rgba(10,11,18,..)` icon-btn (L130,139) → `var(--overlay-scrim)`;
    `#fff` primary text (L103) giữ (chữ trên accent luôn trắng — OK cả 2 theme với accent đậm).
  - `frontend/src/styles/settings-modal.css` (L6) + `image-viewer-modal.css` (L6) — backdrop → `var(--overlay-scrim)`.
  - `frontend/src/styles/palette.css` (L24) — logo `#fff` giữ (trên nền accent).

## Implementation Steps

1. Trong `styles.css`: đổi accent + bảng surface/text/border sang giá trị trung tính (bảng trên),
   gói trong `:root, :root[data-theme="dark"]`.
2. Thêm khối `:root[data-theme="light"]` với bộ giá trị Sáng.
3. Thêm các token mới: `--overlay-scrim`, `--badge-cache-bg/-fg`, `--badge-port-bg/-fg`,
   `--edge`, `--edge-hover`, `--warn` — định nghĩa ở cả 2 theme.
4. Giảm bão hòa `--cat-*` và đổi `--cat-ai` khỏi tím.
5. Tokenize toàn bộ màu hardcode liệt kê ở "Related Code Files".
6. Chạy `npm run dev --prefix frontend`, kiểm tra app vẫn render (vẫn dark, chưa có switch).

## Todo List

- [ ] Tách `:root` → bộ dark + bộ light trong `styles.css`
- [ ] Thêm token overlay/badge/edge/warn cho cả 2 theme
- [ ] Đổi accent sang `#3b6cf0`, giảm bão hòa `--cat-*`, bỏ tím `--cat-ai`
- [ ] Tokenize ~20 màu hardcode (workflow-node, toolbar, react-flow, buttons, modal)
- [ ] Verify build/dev không lỗi, app render bình thường

## Success Criteria

- [ ] `grep` trong `frontend/src/**/*.css` không còn hex/rgba hardcode cho màu nền/chữ/viền
      (cho phép `#fff` trên nền accent + giá trị bên trong định nghĩa token).
- [ ] Tạm set `<html data-theme="light">` thủ công → toàn app đổi sang nền sáng, không
      còn mảng tối kẹt lại.
- [ ] `npm run dev` chạy, không lỗi console CSS.

## Risk Assessment

- **Tương phản chưa đạt** ở light mode (chữ mờ trên nền trắng) → tinh chỉnh `--text-dim/-faint`
  ở Phase 5 QA; bảng trên là điểm xuất phát, không phải con số cuối.
- **Sót màu hardcode** → dùng grep ở Success Criteria làm lưới chặn.
- **`color-mix` support**: đã dùng sẵn trong codebase (workflow-node.css) → trình duyệt mục tiêu OK.
