---
phase: 1
title: Config & Node Cleanup
status: completed
priority: P1
effort: 1h
dependencies: []
---

# Phase 1: Config & Node Cleanup

## Overview
Xóa 3 provider thô (gemini/openai/comfyui) khỏi dropdown chọn provider trong node, và bỏ ô nhập "Model" trong node Tạo/Sửa ảnh. Model từ nay chỉ lấy từ config đã đặt tên. Độc lập, làm trước.

## Requirements
- Functional: dropdown provider trong node chỉ hiện config đã đặt tên (không còn gemini/openai/comfyui thô); node không còn ô text "Model khác"; khi chưa có config nào → node hiển thị/khả dụng mà không crash.
- Non-functional: không phá workflow đang chạy; tương thích metadata sinh động.

## Architecture
- `provider_options()` đang trả `[tên config] + PROVIDER_NAMES`. Bỏ `+ PROVIDER_NAMES`.
- `Param("model")` trong 2 node là nguồn model thứ 2 (cạnh config). Bỏ đi; `run()` chỉ dùng `default_model` từ config.
- **Cạm bẫy:** `Param.to_dict()` (nodes/base.py:33-46) chỉ thêm key `"options"` khi list non-empty. Khi 0 config → `options=[]` → metadata không có `options` → `WorkflowNode.jsx:24` `spec.options.map()` **crash** (undefined). Phải sửa: backend luôn xuất `options` (kể cả rỗng) cho param có `dynamic_options`, HOẶC frontend guard `(spec.options || [])`. Chọn **cả hai** cho chắc (defensive).
- `resolve_model_config()`: bỏ nhánh fallback `if selection in PROVIDER_CLASSES` để chọn provider thô báo lỗi rõ "config không tồn tại, mở ⚙ Cài đặt model". (Giữ `get_provider()`/`make_provider()` cho nội bộ — không xóa, Phase 3 còn dùng.)
- `Param("provider")` default đổi `"gemini"` → `""` (vì gemini thô không còn). `to_dict()` đã tự set default = options[0] khi có dynamic_options + options non-empty, nên default tĩnh chỉ áp dụng khi rỗng.

## Related Code Files
- Modify: `backend/app/providers/__init__.py` — `provider_options()` bỏ `+ PROVIDER_NAMES`; `resolve_model_config()` bỏ nhánh fallback provider thô.
- Modify: `backend/app/nodes/base.py` — `Param.to_dict()`: với param có `dynamic_options`, luôn thêm key `options` (kể cả `[]`).
- Modify: `backend/app/nodes/generate.py` — xóa `Param("model", ...)`; `run()` bỏ `params.get("model") or`; `Param("provider")` default `""`.
- Modify: `backend/app/nodes/edit.py` — như generate.py.
- Modify: `frontend/src/components/WorkflowNode.jsx` — `ParamField` case `'select'`: guard `(spec.options || [])`; nếu select provider mà options rỗng → render hint "Chưa có cấu hình — mở ⚙ Model" thay vì select trống.

## Implementation Steps
1. `providers/__init__.py`: `provider_options()` → `return [c["name"] for c in db.list_model_configs()]`.
2. `providers/__init__.py`: `resolve_model_config()` — bỏ block `if selection in PROVIDER_CLASSES: return make_provider(selection), ""`. Giữ thông báo lỗi cuối hàm (đã có sẵn, đủ rõ).
3. `nodes/base.py` `Param.to_dict()`: sau khi tính `options`, đổi `if options:` → với param dynamic luôn set `d["options"] = options or []`. Cụ thể: `if self.dynamic_options: d["options"] = options or []` còn nhánh tĩnh giữ `elif options: d["options"] = options`.
4. `nodes/generate.py`: xóa dòng `Param("model", "text", ...)`. Trong `run()`: `model=default_model` (bỏ `params.get("model") or`). Đổi `Param("provider", ..., default="gemini", ...)` → `default=""`.
5. `nodes/edit.py`: tương tự — xóa `Param("model")`, `run()` `model=default_model`, provider default `""`.
6. `WorkflowNode.jsx`: case `'select'` → `const opts = spec.options || []`; nếu `opts.length === 0` render `<span className="wf-param-empty">Chưa có cấu hình — mở ⚙ Model</span>`; else render select trên `opts`.
7. Compile check: `backend\.venv\Scripts\python.exe -c "import app.main"` (app-dir backend) để chắc không lỗi import; frontend `npm run build --prefix frontend` hoặc dev khởi động không lỗi.

## Todo List
- [ ] `provider_options()` bỏ PROVIDER_NAMES
- [ ] `resolve_model_config()` bỏ fallback provider thô
- [ ] `Param.to_dict()` luôn xuất options cho param dynamic
- [ ] generate.py: xóa Param model + sửa run() + default provider ""
- [ ] edit.py: xóa Param model + sửa run() + default provider ""
- [ ] WorkflowNode.jsx: guard options rỗng + hint
- [ ] Compile/build check pass

## Success Criteria
- [ ] Dropdown provider trong node chỉ hiện config đặt tên (0 provider thô).
- [ ] Node Tạo/Sửa ảnh không còn ô "Model".
- [ ] Khi DB chưa có config: node render bình thường, hiện hint, không crash console.
- [ ] Chạy node với config hợp lệ vẫn tạo/sửa ảnh OK (gemini/openai key cũ).

## Risk Assessment
- **Workflow cũ lưu provider="gemini" thô** → khi chạy báo lỗi "config không tồn tại". Chấp nhận theo QĐ user (#3). Mitigate: thông báo lỗi đã hướng dẫn mở ⚙ Cài đặt model.
- **Frontend crash options undefined** → đã guard ở bước 3 + 6 (defensive cả 2 đầu).
