# Image Workflow

Công cụ AI tạo/sửa ảnh dạng **workflow kéo thả node** (kiểu ComfyUI/n8n):
mỗi node là một bước (prompt → tạo ảnh → sửa ảnh → biến đổi → lưu), nối dây giữa các node để định nghĩa pipeline.

## Kiến trúc

- **Backend**: Python + FastAPI (`backend/`) — engine thực thi workflow theo thứ tự topo, stream tiến độ qua WebSocket.
- **Frontend**: React + React Flow (`frontend/`) — canvas kéo thả node, xem preview ảnh ngay trên từng node.
- **Provider** (cắm thêm được trong `backend/app/providers/`):
  - `gemini` — Gemini 2.5 Flash Image (Nano Banana), tạo + sửa ảnh theo prompt. Cần `GEMINI_API_KEY`.
  - `openai` — gpt-image-1, tạo + sửa ảnh. Cần `OPENAI_API_KEY`.
  - `codex` — **đăng nhập ChatGPT (OAuth)** thay vì API key: dùng quota gói ChatGPT qua endpoint Codex (`backend-api/codex/responses`). Tạo + sửa ảnh (đã chạy thật với gpt-5.5).
  - `comfyui` — Stable Diffusion local qua server ComfyUI đang chạy (txt2img / img2img). Cấu hình `COMFYUI_URL`.

> Đăng nhập ChatGPT (provider `codex`): mở **⚙ Cài đặt** → chọn provider "OpenAI (đăng nhập ChatGPT)" → bấm **Đăng nhập OpenAI**. Token dùng chung file `~/.codex/auth.json` với Codex CLI (nếu đã `codex login` thì nhận luôn). Đây là endpoint nội bộ ChatGPT, không phải API chính thức — dùng cho mục đích cá nhân.
>
> Lưu ý model: `gpt-5.5` chỉ là model "host" điều khiển tool `image_generation` — ảnh thực tế do model gpt-image sinh nội bộ (server tự chọn). Soi lỗi khi tạo ảnh treo/thất bại: đặt `CODEX_DEBUG=1` trong `.env` → mỗi request ghi log đầy đủ request body + từng event SSE vào `logs/codex/*.log` (không ghi token). Request quá 300s chưa ra ảnh sẽ tự hủy với lỗi rõ ràng thay vì chạy vô hạn.

> Chọn model: ô **Model** trong ⚙ Cài đặt là dropdown — có sẵn danh sách model curated theo provider; bấm **⟳** để tải danh sách model thật từ API (Gemini / OpenAI / checkpoint ComfyUI); hoặc chọn **✎ Nhập tay** để gõ tên model tự do. Bỏ trống = model mặc định của provider.

## Cài đặt

```powershell
# 1. Backend (đã có sẵn venv nếu bạn chạy bước setup)
python -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt

# 2. Frontend
npm install --prefix frontend

# 3. API key
copy .env.example .env   # rồi điền GEMINI_API_KEY / OPENAI_API_KEY
```

## Chạy

```powershell
# Terminal 1 — backend (cổng 8000). Thêm --reload khi đang dev.
# Dùng script này (KHÔNG gọi uvicorn CLI trực tiếp): script tắt keepalive ping WS
# (ws_ping_interval=None) — pong qua proxy Vite không về kịp làm uvicorn tự ngắt
# kết nối ("keepalive ping timeout") khi node AI chạy lâu >40s; CLI không truyền
# được None nên phải qua Python API.
backend\.venv\Scripts\python backend\run_server.py

# Terminal 2 — frontend (cổng 5173)
npm run dev --prefix frontend
```

Mở http://localhost:5173, kéo node từ thanh bên trái vào canvas, nối dây, bấm **▶ Chạy**.

## Các node có sẵn

| Node | Nhóm | Chức năng |
|---|---|---|
| Prompt | Đầu vào | Nhập text/prompt |
| Tải ảnh lên | Đầu vào | Upload ảnh từ máy + ô **Mô tả ảnh** (đặt tên ảnh; đi theo ảnh xuống node Sửa ảnh) |
| Ghép prompt | Đầu vào | Nối nhiều đoạn text thành một, mỗi đoạn một dòng (nối bao nhiêu dây cũng được) |
| Tạo ảnh (AI) | AI | Text → ảnh (chọn cấu hình model đã đặt tên trong ⚙ Cài đặt) + ô **Mô tả ảnh** |
| Sửa ảnh (AI) | AI | Ảnh + prompt → ảnh đã sửa (đổi nền, thêm chi tiết, đổi style...) |
| Trích vùng (AI) | AI | Ảnh + mô tả đối tượng → AI tìm vùng → crop giữ nguyên pixel gốc (mặt/người/áo/con vật...). Pre-process trước khi ghép. Cần provider vision (Gemini / OpenAI / Codex) |
| Resize | Biến đổi | Đổi kích thước |
| Bộ lọc | Biến đổi | Trắng đen / blur / sharpen... |
| Chỉnh màu | Biến đổi | Sáng / tương phản / bão hòa |
| Lưu ảnh | Đầu ra | Lưu vào `outputs/` |

## Xem & tải ảnh

Mọi node hiển thị ảnh (Tải ảnh lên / Tạo ảnh / Sửa ảnh / Lưu ảnh / Biến đổi):
**bấm vào ảnh** → mở cửa sổ xem ảnh full-res, có nút **Tải ảnh gốc** (ảnh PNG gốc,
không phải bản thu nhỏ) và mở tab mới. Đóng bằng nút ✕, phím Esc, hoặc bấm ra nền.

Ảnh gốc của node AI/Biến đổi lấy từ cache blob qua `/api/cache-image/{sha}` (preview
trên node chỉ là thumbnail nhẹ để hiển thị nhanh). Node Tải ảnh lên chỉ hiện 1 ảnh
(ngay tại ô upload).

## Ví dụ workflow

`Prompt("một chú mèo phi hành gia") → Tạo ảnh (gemini) → Sửa ảnh ("đổi nền thành sao Hỏa") → Resize → Lưu ảnh`

Workflow mẫu có sẵn trong `workflows/` — bấm **📂 Mở...** trên thanh công cụ để tải.

## Mô tả ảnh → phân biệt ảnh trong node Sửa ảnh (Ảnh 1 / Ảnh 2)

Node nguồn (**Tải ảnh lên**, **Tạo ảnh**) có ô **"Mô tả ảnh"**: vừa làm phụ đề trên
node (đặt tên ảnh cho dễ nhìn), vừa **đi theo ảnh** xuống node **Sửa ảnh**. Khi nhiều
ảnh nối vào Sửa ảnh, engine tự ghép khối tham chiếu đánh số trước prompt:

```
Ảnh đầu vào:
- Ảnh 1: cái áo sơ mi trắng
- Ảnh 2: người mẫu nữ
```

→ AI biết "Ảnh 1/Ảnh 2" là gì. Ví dụ workflow đa-ảnh:

`Tải ảnh lên("cái áo sơ mi trắng") + Tải ảnh lên("người mẫu nữ") → Sửa ảnh ("mặc áo ở Ảnh 1 lên người ở Ảnh 2")`

- Đánh số theo thứ tự ảnh: ảnh gốc = **Ảnh 1**, rồi cổng "Ảnh ghép thêm" theo thứ tự nối.
- Ảnh nối nhưng để trống mô tả → vẫn liệt kê `Ảnh N: (không mô tả)` (số không nhảy).
- Không ảnh nào có mô tả → prompt giữ NGUYÊN như cũ.
- Mô tả **chảy qua** node Biến đổi (Resize/Bộ lọc/Chỉnh màu) — nhãn sống sót.
- **Đổi mô tả KHÔNG sinh lại ảnh AI** (không tốn token) nhưng node Sửa ảnh phía dưới chạy lại với prompt mới — xem mục Cache.

> **Neo identity (Codex/Gemini):** 2 provider này còn xen caption `Ảnh N: <tên>` **ngay trước từng ảnh** trong request → model bám đúng "ảnh nào là ai", giảm lỗi bốc nhầm mặt khi ghép nhiều người. Kèm chỉ thị "giữ nguyên nhận dạng, không tráo mặt". OpenAI (Images-Edit API) và ComfyUI không xen được → chỉ dùng khối text ở trên. Lưu ý: ghép nhiều khuôn mặt thật trong 1 lần gọi vẫn là giới hạn của model sinh ảnh — caption tăng tỉ lệ đúng chứ không đảm bảo tuyệt đối.

> **Mẹo chất lượng mặt:** muốn AI giữ đúng mặt một người, ảnh nguồn nên là **chân dung rõ mặt** (mặt chiếm phần lớn khung). Ảnh chụp xa, người nhỏ giữa khung cảnh rộng → vùng mặt quá ít pixel → AI không trích đủ để giữ → dễ ghép sai mặt. Crop sát người trước khi upload.

> **Upload tự chuẩn hóa:** ảnh upload được tự thu nhỏ về cạnh dài ≤ 2048px + nén (có trong suốt → PNG, còn lại → JPEG), chặn file > 40MB. Tránh upload vài chục MB làm phình cache + nặng request AI.

## Cache theo node + chạy từng node (kiểu n8n)

Engine **nhớ kết quả từng node** trên đĩa (`cache/`, sống qua `--reload`) theo
`node_key = sha256(type + params + output_key node cha + hash source code node)`.
Chạy lại workflow → node nào **không đổi** sẽ dùng lại output cache (badge **⚡ cache**),
**KHÔNG gọi lại provider AI** → tiết kiệm token. Đổi param/đầu vào/sửa code node →
key đổi, lan xuống → node đó + downstream chạy lại; nhánh khác vẫn cache-hit.

- **▶ trên từng node** — chạy tới node đó (tổ tiên dùng cache), ép chính node đó sinh mới (xem output / ép tạo ảnh mới).
- **▶ Chạy** (toolbar) — chạy tổng, cache-aware (chỉ chạy lại node đã đổi + downstream).
- **🗑 Xóa cache** (toolbar) — xóa sạch cache; lần chạy kế chạy lại tất cả. Cũng có `POST /api/cache/clear`.
- Ảnh cache dedupe theo nội dung; tổng vượt `CACHE_MAX_BYTES` (mặc định 500MB, đặt trong `.env`) → tự xóa blob cũ nhất.
- Lưu ý: sửa model **sau lưng** một cấu hình đã đặt tên (giữ nguyên tên) KHÔNG tự vô hiệu cache (key theo tên cấu hình) → bấm 🗑 Xóa cache nếu muốn sinh lại.
- Ô **"Mô tả ảnh"** KHÔNG tính vào `node_key` (đổi mô tả ≠ sinh lại ảnh AI) nhưng nối hash vào `output_key` của ảnh → node Sửa ảnh phía dưới chạy lại với prompt mới.

## Harness mode — chạy lặp tới khi đạt (critic-refine)

Nút **▶ Harness** (cạnh ▶ Chạy) chạy workflow như một *harness*: sau mỗi lần chạy,
một **AI critic (vision)** tự chấm ảnh sản phẩm cuối so với mục tiêu → chưa đạt thì
**chèn phản hồi vào prompt node sinh** rồi chạy lại → lặp tới khi **đạt** hoặc **hết
số vòng**. Kết quả cuối = **iteration điểm cao nhất** + báo cáo điểm/feedback từng vòng.

- **Mục tiêu (goal)** lấy **tự động** = prompt hiệu dụng của node Tạo/Sửa ảnh terminal
  (gồm cả prompt nối từ cổng). Không phải nhập lại.
- **Cấu hình** (popover nút Harness): *Số vòng tối đa* (mặc định 3), *Ngưỡng đạt* (0–10,
  mặc định 8), *Critic* (cấu hình Gemini để chấm — trống thì dùng provider của node sinh),
  *Tiêu chí đạt* (tùy chọn — ví dụ "mặt rõ, đúng người, nền sạch").
- **Cần provider vision** để chấm ảnh: **Gemini** (bbox grounding native, chính xác nhất),
  **OpenAI** (gpt-4o vision) hoặc **Codex** (đăng nhập ChatGPT — gpt-5.5 multimodal).
  ComfyUI không có VLM → báo lỗi rõ **trước khi** sinh (không tốn lượt). Lưu ý: `gpt-image-*`
  là model *sinh ảnh*, không chấm/trích được — tự chuyển sang model vision khi cần.
- **Token-aware**: dừng sớm khi đạt; node không đổi vẫn cache-hit; có giới hạn vòng cứng.
- Node lỗi giữa chừng → vẫn **giữ + lưu bản tốt nhất** đã có + báo "dừng sớm".
- **Chạy thường (▶ Chạy)** không đổi gì — harness là đường riêng, opt-in.

> Node **Sửa ảnh** có thêm ô **"Chỉ thị hệ thống (tùy chọn)"**: đè chỉ thị giữ-nhận-dạng
> mặc định ("không tráo mặt") khi ý đồ workflow khác (vd chỉ đổi nền). Trống → giữ mặc định.

## Test node offline (không tốn token)

Provider **`fake`** vẽ ảnh PNG placeholder + echo text, **không gọi mạng**. Tạo một
cấu hình provider `fake` trong ⚙ Cài đặt để chạy thử node `Tạo ảnh`/`Sửa ảnh`/`Enhance prompt`
mà không tốn token. Chạy thử 1 node ở terminal:

```powershell
cd backend
.venv\Scripts\python.exe run_node.py --type generate_image --param prompt="mèo" --fake --out .
.venv\Scripts\python.exe run_node.py --type resize --input image=in.png --param width=128 --param height=128 --out .
```

`--fake` ép mọi node AI dùng FakeProvider; `--input handle=path` nạp ảnh (bytes),
`--input-text handle=giá_trị` nạp text, `--param k=v` đặt tham số (lặp được).

## Thêm node / provider mới

- **Node mới**: tạo class trong `backend/app/nodes/`, kế thừa `BaseNode`, gắn decorator `@register_node`, khai báo `inputs/outputs/params` — UI tự sinh form, không cần sửa frontend.
- **Provider mới**: kế thừa `ImageProvider` trong `backend/app/providers/`, implement `generate()` và `edit()`, đăng ký trong `providers/__init__.py`.
