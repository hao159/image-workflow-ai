---
phase: 3
title: Frontend harness UI + docs
status: completed
priority: P2
effort: 1-1.5d
dependencies:
  - 2
---

# Phase 3: Frontend harness UI + docs

## Overview

UI cho harness: nút **"▶ Chạy (harness)"** + config (criteria/max/threshold/critic); hiển thị iteration (điểm/feedback) + report khi nhận `harness_iteration`/`harness_report`. Cập nhật README + memory.

> **Red-team đã sửa (C11):** frontend KHÔNG modular như giả định — toàn bộ run/WS nằm trong **1 file `App.jsx` (~563 dòng)**: nút Chạy inline (`App.jsx:456`), WS `onmessage` switch (`App.jsx:302-340`), `RunContext.jsx` chỉ là stub 13 dòng. Không có `Toolbar.jsx`/store. Effort + scope điều chỉnh theo thực tế; cân nhắc tách logic run khỏi `App.jsx` (quy tắc 200 dòng trong CLAUDE.md).

## Requirements
- Functional:
  - Nút riêng "▶ Chạy (harness)" cạnh "▶ Chạy" (`App.jsx:456`), giữ chạy thường nguyên.
  - Config nhỏ: ô **tiêu chí (tùy chọn)**, **max vòng** (default 3), **ngưỡng đạt** (default 8), **critic provider** (chọn cấu hình vision, default Gemini). Gửi `harness:{enabled:true,...}` trong envelope WS.
  - `App.jsx:309-320` switch thêm case `harness_iteration` → log "Vòng N: điểm X — pass/fail" + feedback; `harness_report` → hiện best + lý do. Ảnh best hiển thị như node_finished thường.
- Non-functional: switch `default` bỏ qua type lạ (backward — server cũ/run thường không gửi event mới). Chạy thường KHÔNG gửi field harness.

## Architecture
- Tích hợp vào file thật (đã scout — C11):
  - `App.jsx:302-340` — WS connect + `onmessage` switch: thêm 2 case + state run-mode (iteration/score/report).
  - `App.jsx:456` — thêm nút harness + popover config.
  - `App.jsx:288-292` — run-start reset state: thêm reset state harness.
  - Cân nhắc tách phần run/WS thành module riêng (giảm `App.jsx` < 200 dòng) — quyết khi code, không bắt buộc MVP.
- Không đổi node rendering (form tự sinh từ metadata).

## Related Code Files
- Modify: `frontend/src/App.jsx` (nút + config + WS send harness + handle 2 event mới + reset state)
- Modify: `frontend/src/RunContext.jsx` (nếu cần giữ state harness — hiện là stub)
- Modify: `README.md` (mục "Harness mode")
- Modify: memory `image-workflow-project.md`

## Implementation Steps
1. (Scout đã xong — dùng file thật trên.) Thêm nút "▶ Chạy (harness)" + popover config.
2. WS send: envelope gắn `harness` khi bấm nút harness; nút thường không gắn.
3. WS receive: 2 case mới → panel/log iteration + report; ảnh best hiển thị.
4. Reset state harness ở run-start.
5. `npm run build --prefix frontend` sạch.
6. README: mục "Harness mode (chạy lặp tới khi đạt)" — critic/limit/best+report, lưu ý cần provider vision (Gemini). (Node trích KHÔNG ở phase này — đã tách.)
7. Memory project cập nhật.
8. **(Manual, chờ user)** verify e2e: workflow + harness on → iteration + report + ảnh best trên canvas.

## Success Criteria
- [ ] Nút "▶ Chạy (harness)" + config hoạt động; chạy thường không đổi.
- [ ] UI hiện iteration (điểm/pass/feedback) + report best; ảnh best hiển thị.
- [ ] `npm run build` sạch; switch default bỏ qua type lạ.
- [ ] README + memory cập nhật.

## Risk Assessment
- **`App.jsx` quá lớn** → tránh phình thêm; cân nhắc tách run/WS module (C11).
- **WS event mới vỡ handler cũ** → default case an toàn.
- **UX harness rối** → panel tối giản MVP.
