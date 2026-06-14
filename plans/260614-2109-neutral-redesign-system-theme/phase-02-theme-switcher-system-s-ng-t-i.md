---
phase: 2
title: Theme switcher (System/Sáng/Tối)
status: completed
priority: P1
effort: 3-4h
dependencies:
  - 1
---

# Phase 2: Theme switcher (System/Sáng/Tối)

## Overview

Thêm cơ chế chọn theme: **Hệ thống / Sáng / Tối**, lưu localStorage, áp ngay bằng cách
set `data-theme` trên `<html>`. Khi ở chế độ "Hệ thống" thì bám `prefers-color-scheme`
và đổi theo OS realtime. UI điều khiển đặt trong section "Giao diện" của Cài đặt.

## Requirements

- Functional: chọn 1 trong 3 mode; "Sáng"/"Tối" ép cứng; "Hệ thống" theo OS realtime;
  lựa chọn nhớ qua reload.
- Non-functional: không nhấp nháy theme khi load (apply trước paint); KISS — tái dùng
  pattern localStorage sẵn có trong `ui-settings.js`.

## Key Insights

- `ui-settings.js` đã có pattern đọc/ghi localStorage + cache (runEffect) → mở rộng thêm
  `theme` cùng kiểu, không tạo file mới.
- SettingsModal đã có sẵn section "Giao diện" (`SettingsModal.jsx:94-110`) → cắm control
  theme vào ngay đó, đồng dạng với dropdown hiệu ứng.
- Tránh FOUC: set `data-theme` **trước khi React render**, ngay trong `main.jsx` (hoặc
  một snippet đầu `index.html`). Đặt trong `main.jsx` trước `createRoot` là đủ và gọn.

## Architecture

- **State machine theme:**
  - `themeSetting` ∈ `{system, light, dark}` (lưu localStorage key `iw-ui-settings.theme`).
  - `resolvedTheme` = `themeSetting === 'system' ? matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light' : themeSetting`.
  - Áp: `document.documentElement.setAttribute('data-theme', resolvedTheme)`.
- **Realtime OS change:** đăng ký `matchMedia(...).addEventListener('change', ...)` — chỉ
  re-apply khi `themeSetting === 'system'`. Gắn 1 lần ở `main.jsx` (module scope) hoặc
  trong hàm `initTheme()`.
- **React Flow `colorMode`** (App.jsx:628 đang cứng `"dark"`) cần biết theme hiện tại →
  expose `resolvedTheme` cho App qua một hook/subscribe nhỏ (xem bước 4). Phase 4 dùng
  giá trị này; Phase 2 chỉ cần dựng nguồn dữ liệu.

## Related Code Files

- Modify: `frontend/src/ui-settings.js` — thêm:
  - `THEME_OPTIONS = [{value:'system',label:'Theo hệ thống'},{value:'light',label:'Sáng'},{value:'dark',label:'Tối'}]`
  - `getThemeSetting()`, `setThemeSetting(v)` (đồng pattern getRunEffect/setRunEffect).
  - `resolveTheme()` → trả 'light'|'dark' theo setting + matchMedia.
  - `applyTheme()` → set `data-theme` lên `<html>`.
  - `initThemeWatcher(onChange)` → đăng ký matchMedia change; gọi `applyTheme` + callback.
- Modify: `frontend/src/main.jsx` — gọi `applyTheme()` trước `createRoot(...).render(...)`
  (chống FOUC) + `initThemeWatcher()` để theo OS realtime.
- Modify: `frontend/src/components/SettingsModal.jsx` — thêm control chọn theme trong
  section "Giao diện" (radio segmented hoặc `<select>` đồng dạng dropdown hiệu ứng);
  onChange → `setThemeSetting` + `applyTheme` + cập nhật state local.

## Implementation Steps

1. `ui-settings.js`: thêm các hàm theme ở trên. `resolveTheme` đọc `matchMedia`.
   `applyTheme` set attribute. Cache giống `runEffect`.
2. `main.jsx`: `import { applyTheme, initThemeWatcher } from './ui-settings.js'`; gọi
   `applyTheme()` ngay trước render; `initThemeWatcher()` sau (cập nhật khi OS đổi + khi
   setting = system). Watcher cũng cần thông báo cho App (React Flow colorMode) — dùng
   một `CustomEvent('iw-theme-change')` trên `window` hoặc callback store nhẹ.
3. `SettingsModal.jsx`: render control 3 lựa chọn (ưu tiên segmented control 3 nút cho rõ;
   fallback `<select>` nếu muốn tối giản). State `themeSetting` khởi từ `getThemeSetting()`.
4. App nghe `iw-theme-change` (hoặc `getResolvedTheme()` + re-render) để truyền
   `colorMode={resolvedTheme}` cho `<ReactFlow>` — Phase 4 hoàn thiện phần React Flow,
   Phase 2 chỉ cần cơ chế phát tín hiệu sẵn sàng.

## Todo List

- [ ] Thêm theme API vào `ui-settings.js` (get/set/resolve/apply/watch)
- [ ] Áp theme trước render trong `main.jsx` (chống FOUC) + watcher OS realtime
- [ ] Control 3 lựa chọn trong section "Giao diện" của SettingsModal
- [ ] Phát tín hiệu theme cho App (cho React Flow colorMode ở Phase 4)
- [ ] Verify: chọn Sáng/Tối ép cứng; System đổi theo OS; nhớ qua reload; không nhấp nháy

## Success Criteria

- [ ] Đổi mode trong Cài đặt → app đổi nền ngay, không reload.
- [ ] Mode "Hệ thống" + đổi theme OS (Windows light/dark) → app tự đổi realtime.
- [ ] Reload trình duyệt → giữ đúng mode đã chọn, không thấy chớp theme cũ.
- [ ] Không lỗi console.

## Risk Assessment

- **FOUC** nếu apply sau React mount → bắt buộc apply trong `main.jsx` trước render.
- **Đồng bộ React Flow colorMode**: nếu App không re-render khi theme đổi, canvas giữ
  màu cũ → dùng CustomEvent + state ở App (chốt ở Phase 4). Ghi rõ để không bỏ sót.
- **matchMedia listener leak**: đăng ký ở module scope/`init` 1 lần, không trong render loop.
