# 2026-06-15 — Đóng gói app thành file .exe tự chứa (Windows, PyInstaller onedir)

## Mục tiêu
Ship app cho người không-dev: double-click 1 chỗ là chạy, máy đích không cần Python/Node.

## Quyết định
- **onedir** (không onefile): khởi động nhanh, ít bị antivirus chặn.
- **Backend phục vụ luôn SPA** cùng origin → bỏ Vite ở bản đóng gói. Khả thi vì frontend
  vốn dùng URL tương đối (`/api`) + `location.host` cho WS → **0 thay đổi frontend**.
- API key **nhập qua ⚙ Cài đặt** (đã lưu SQLite), không nhúng vào exe.

## Cái khó đáng nhớ
1. **Data-dir khi frozen:** `config.py` dùng `parents[2]` của `__file__` → trong bundle
   PyInstaller `__file__` nằm trong thư mục giải nén tạm (read-only). Fix: khi `sys.frozen`
   → `ROOT_DIR = Path(sys.executable).resolve().parent` (ghi được, cạnh exe); `SPA_DIR` từ
   `sys._MEIPASS/frontend_dist`.
2. **Thứ tự mount:** `StaticFiles("/")` phải đăng ký **cuối cùng** (sau mọi `/api/*` + `/ws/run`)
   vì Starlette khớp route theo thứ tự đăng ký. Guard `SPA_DIR.is_dir()` để dev (Vite) bỏ qua mount.
3. **WS keepalive:** launcher mới (`desktop_app.py`) phải giữ `ws_ping_interval=None` như
   `run_server.py` — nếu không, node AI chạy >40s bị ngắt WS, ảnh sinh xong không hiện.
4. **PyInstaller imports:** providers/nodes import **tĩnh** trong `__init__` → static analysis
   bắt được; vẫn thêm `collect_submodules('app','uvicorn')` + `collect_all('google.genai',
   'openai','certifi')` cho chắc. `openai.helpers` cảnh báo thiếu numpy (voice_helpers) — vô hại.

## Kết quả (đã kiểm chứng trên exe thật)
- Boot sạch, serve SPA, **11 node-types + 5 provider** đầy đủ, data tạo cạnh exe + sống dai.
- Live test **e2e** (upload→run→output) + **ws_cache** PASS với mount bật → không regression.
- Bundle 62 MB. Code review: không lỗi nghiêm trọng.

## Còn lại
- `console=True` (thấy log/lỗi khi mới ship); muốn ẩn terminal → sửa `console=False` trong spec.
- exe đã build trước fix `sys.executable.resolve()` 1 chữ — hành vi giống nhau trên path
  thường; lần build kế tự cập nhật.
- Test thật trên máy KHÔNG có Python (VM/máy khác) là kiểm tra residual nên làm.

## File
config.py, main.py, desktop_app.py (mới), build/imageworkflow.spec + build.ps1 (mới),
.gitignore, README. Commit `0fc6043`. Plan: `plans/260615-2230-package-app-single-exe-windows/`.
