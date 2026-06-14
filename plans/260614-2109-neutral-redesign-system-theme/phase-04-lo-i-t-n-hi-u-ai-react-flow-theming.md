---
phase: 4
title: Loại tín hiệu AI & React Flow theming
status: completed
priority: P2
effort: 3-5h
dependencies:
  - 1
  - 2
  - 3
---

# Phase 4: Loại tín hiệu AI & React Flow theming

## Overview

Gỡ các tín hiệu "hơi hướng AI" còn lại: **icon Sparkles** cho node AI, **hiệu ứng glow/scan/
pulse neon** khi node chạy, **strip accent phát sáng** trên header. Đồng thời cho **React Flow
(canvas, edges, background, minimap, controls) đổi theo theme** thay vì cứng dark.

## Requirements

- Functional: node AI vẫn nhận diện được (icon trung tính thay sparkles); trạng thái chạy
  vẫn thấy rõ (chỉ báo phẳng, không neon); canvas đúng màu theo theme.
- Non-functional: giữ tùy chọn hiệu ứng trong Cài đặt nhưng đổi mặc định sang phẳng;
  reduced-motion vẫn được tôn trọng.

## Key Insights

- "AI vibe" động đến từ: `SparklesIcon` (icons.jsx) gán cho category AI
  (`node-category-styles.js:8`), và 3 hiệu ứng `glow/scan/pulse` (workflow-node.css:310-341,
  ui-settings.js RUN_EFFECT_OPTIONS).
- Không nên xóa cơ chế hiệu ứng (đã có UI chọn) → thay bằng **chỉ báo chạy phẳng** làm
  mặc định: viền `--run` + nhẹ nhàng (không neon glow lớn). Giữ option cho ai thích.
- React Flow: `colorMode` (App.jsx:628) + `Background color` (L631) cứng → nối vào
  `resolvedTheme` (Phase 2). Edge stroke đã tokenize ở Phase 1 (`--edge`).

## Architecture

- **Icon node AI:** đổi `SparklesIcon` → icon trung tính (đề xuất: `WandIcon`/`CpuIcon`/
  một icon hình ảnh như `ImageIcon` đã có, hoặc `WrenchIcon`). Chọn icon không gợi "magic AI".
  Quyết định cuối khi thực thi; mặc định đề xuất: dùng icon kiểu "layers/image" trung tính.
- **Run effects:**
  - Đổi mặc định `runEffect` từ `auto` (glow/scan/pulse) → `'solid'` (chỉ báo phẳng).
  - Thêm option `'solid'` vào `RUN_EFFECT_OPTIONS`: viền `--run` + bóng rất nhẹ, không animation.
  - Giữ glow/scan/pulse là lựa chọn nâng cao (đổi tên nhãn cho rõ "hiệu ứng động").
  - Giảm cường độ glow/scan (bỏ neon `0 0 26px`) hoặc giữ nguyên (vì opt-in) — quyết khi QA.
- **Header strip:** `.wf-node-header::before` (strip accent 2px) giữ lại nhưng dùng
  `--node-accent` đã giảm bão hòa (Phase 1) → đủ phân nhóm, không chói. Bỏ `::after` scan
  khỏi mặc định (chỉ bật khi chọn effect scan).
- **React Flow theme:**
  - `colorMode={resolvedTheme}` (lấy từ state theme ở App, Phase 2).
  - `<Background color="var(--rf-grid)" />` — thêm token `--rf-grid` (dark `#262b35` /
    light `#dfe3ea`). React Flow Background nhận màu trực tiếp; nếu không nhận `var()` thì
    đọc từ computed style hoặc đặt 2 giá trị theo theme qua biến JS.
  - minimap-mask/node, controls đã token hóa ở Phase 1 → kiểm lại ở light.

## Related Code Files

- Modify: `frontend/src/node-category-styles.js` — đổi `Icon` của category `AI` khỏi
  `SparklesIcon`; đổi `runEffect` mặc định mỗi nhóm sang `'solid'` (hoặc null).
- Modify: `frontend/src/components/icons.jsx` — nếu cần thêm icon trung tính mới cho node AI.
- Modify: `frontend/src/ui-settings.js` — thêm `'solid'` vào `RUN_EFFECT_OPTIONS`, đổi
  mặc định `getRunEffect` về `'solid'`; `resolveRunEffect` xử lý `'solid'`.
- Modify: `frontend/src/styles/workflow-node.css` — thêm class `.effect-solid` (viền `--run`
  phẳng); cân chỉnh glow/scan/pulse cho bớt neon; `::before` strip dùng accent dịu;
  `::after` scan chỉ trong `.effect-scan`.
- Modify: `frontend/src/App.jsx` — `colorMode` động theo theme; `<Background>` màu theo token;
  subscribe `iw-theme-change` (Phase 2) để re-render canvas.
- Modify: `frontend/src/styles/react-flow-overrides.css` — thêm `--rf-grid` usage nếu cần;
  verify edge/minimap/controls ở light.

## Implementation Steps

1. Đổi icon category AI trong `node-category-styles.js` (+ thêm icon nếu cần ở icons.jsx).
2. `ui-settings.js`: thêm option `'solid'`, đổi mặc định, cập nhật `resolveRunEffect`.
3. `workflow-node.css`: thêm `.effect-solid`; tách `::after` scan vào `.effect-scan`;
   giảm neon ở glow/pulse; strip header dùng accent dịu.
4. `App.jsx`: nối `colorMode` + `<Background color>` vào `resolvedTheme`/token; lắng nghe
   sự kiện theme để canvas đổi màu realtime.
5. Kiểm node AI ở canvas: icon mới hiển thị, không còn sparkles.
6. Chạy workflow thử (provider `fake`) → trạng thái chạy hiển thị phẳng, dây nối đổi
   màu `--run`, không neon.
7. Soát canvas/minimap/controls/edges ở cả Sáng & Tối.

## Todo List

- [ ] Đổi icon node AI khỏi Sparkles (+ icon mới nếu cần)
- [ ] Thêm chỉ báo chạy `'solid'`, đặt làm mặc định; giữ hiệu ứng động là opt-in
- [ ] Giảm/khoanh vùng glow/scan/pulse; tách scan vào class riêng
- [ ] React Flow colorMode + Background + minimap/controls theo theme (realtime)
- [ ] Soát canvas ở cả 2 theme khi chạy workflow (fake provider)

## Success Criteria

- [ ] Node AI không còn icon sparkles; không còn glow/scan neon ở chế độ mặc định.
- [ ] Chạy workflow: trạng thái node + dây nối vẫn thấy rõ nhưng phẳng, trung tính.
- [ ] Canvas/grid/minimap/controls đổi đúng theo Sáng/Tối, kể cả khi đổi theme realtime.
- [ ] Tùy chọn hiệu ứng động vẫn chọn được trong Cài đặt (không xóa tính năng).

## Risk Assessment

- **`<Background color>` không nhận CSS var:** nếu vậy, truyền giá trị màu qua JS theo
  `resolvedTheme` (2 hằng số) thay vì `var()`. Ghi rõ fallback.
- **Mất tín hiệu trạng thái khi bỏ glow:** chỉ báo `'solid'` phải đủ tương phản (viền
  `--run` + nền header nhẹ) để vẫn thấy node đang chạy — kiểm ở Phase 5.
- **Đổi mặc định runEffect ảnh hưởng user cũ:** người đã lưu `auto` trong localStorage vẫn
  giữ lựa chọn cũ (chỉ default mới đổi) — chấp nhận; không migrate cưỡng bức.
