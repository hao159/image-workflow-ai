---
phase: 4
title: "Frontend: tab hóa modal Cài đặt (Giao diện | Model)"
status: pending
priority: P2
effort: "3h"
dependencies: []
status: completed
---

# Phase 4: Frontend — tab hóa modal Cài đặt

## Overview
`SettingsModal.jsx` (255 dòng, >200 → cần tách) hiện là 1 trang dài: mục **Giao diện** (theme + hiệu ứng node) rồi mục **Model** (bảng cấu hình + form + OAuth). Chia thành **2 tab: Giao diện | Model** (OAuth nằm trong tab Model theo provider codex).

## Requirements
- Functional:
  - Modal Cài đặt có thanh tab trên cùng: **Giao diện** | **Model**. **Mặc định mở tab Model** (khớp hành vi cũ "mở ra thấy bảng cấu hình" — quyết định validation).
  - Tab **Giao diện**: theme seg (Hệ thống/Sáng/Tối) + select hiệu ứng node.
  - Tab **Model**: hint + bảng cấu hình + form thêm/sửa (gồm OAuth box khi provider=codex).
  - State tab giữ trong phiên mở modal; đổi tab không mất dữ liệu form đang nhập.
- Non-functional: tách file để mỗi file < 200 dòng (modularization rule).

## Architecture
- Tách `SettingsModal.jsx` thành:
  - `frontend/src/components/settings-appearance-tab.jsx` — UI Giao diện (nhận/đặt theme + runEffect qua `ui-settings.js`).
  - `frontend/src/components/settings-model-tab.jsx` — bảng + form cấu hình + OAuth (giữ logic `configs`, `form`, `submit`, `remove`, `login`, `ModelField`).
  - `SettingsModal.jsx` còn lại: khung modal + state `activeTab` (**khởi tạo = `'model'`**) + render tab. Giữ prop `onClose`, `onChanged` (truyền xuống model tab).
- **CSS** `frontend/src/styles/settings-modal.css`: thêm `.settings-tabs` (thanh tab) + `.settings-tab-btn.active`. Tái dùng token theme + style giống `.theme-seg` cho nhất quán.

## Related Code Files
- Create: `frontend/src/components/settings-appearance-tab.jsx`, `frontend/src/components/settings-model-tab.jsx`
- Modify: `frontend/src/components/SettingsModal.jsx` (khung + tab), `frontend/src/styles/settings-modal.css`
- Read context: `frontend/src/ui-settings.js`, `frontend/src/components/model-field.jsx`

## Implementation Steps
1. Tạo `settings-appearance-tab.jsx`: chuyển block "Giao diện" (theme seg + run effect). Tự quản state hiển thị từ `ui-settings.js` getters.
2. Tạo `settings-model-tab.jsx`: chuyển toàn bộ logic model (`configs/form/submit/remove/login/oauth`) + JSX bảng/form/OAuth + `<ModelField>`. Nhận `onChanged`.
3. `SettingsModal.jsx`: rút gọn còn khung modal + `activeTab` state + thanh `.settings-tabs` + render tab tương ứng.
4. CSS thanh tab.
5. Build + mở Cài đặt: đổi tab, thêm/sửa/xóa cấu hình, đổi theme realtime, đăng nhập codex — đều chạy như cũ.

## Success Criteria
- [ ] Modal Cài đặt có 2 tab Giao diện | Model, chuyển tab mượt, không mất form đang nhập.
- [ ] Tab Giao diện: đổi theme áp ngay; đổi hiệu ứng node lưu localStorage.
- [ ] Tab Model: bảng + thêm/sửa/xóa + OAuth (codex) hoạt động y như trước.
- [ ] Mỗi file mới < 200 dòng; `SettingsModal.jsx` thu gọn rõ.
- [ ] Build frontend pass; không regression chức năng cũ.

## Risk Assessment
- **Regression khi tách logic model**: nhiều state liên quan (`form`, `editing`, `providerMeta`). Mitigation: bê nguyên khối logic vào 1 component, không tái cấu trúc logic — chỉ di chuyển.
- **`onChanged` callback**: phải truyền tới model tab để `refreshNodeTypes` của App vẫn chạy sau khi sửa cấu hình.

## Security Considerations
- Không đổi xử lý API key (vẫn password input + preview mask phía backend).

## Next Steps
- Phase 5 QA + cập nhật ghi chú UI nếu README mô tả Cài đặt.
